import cv2
import numpy as np
from collections import deque

# Import the classes from the modules we just built
from preprocessing import Preprocessor
from filtering import SignalFilter
from rakf import RAKF
from hr_estimation import HREstimator

def main():
    # --- 1. Initialize Pipeline Modules ---
    fps = 30
    window_seconds = 10
    buffer_size = fps * window_seconds  # 300 frames
    
    preprocessor = Preprocessor()
    sig_filter = SignalFilter(fps=fps)
    rakf = RAKF(initial_hr=75.0)
    estimator = HREstimator(fps=fps)
    
    # Volatile memory buffer for the sliding window
    raw_signal_buffer = deque(maxlen=buffer_size)
    
    # Initialize standard webcam capture 
    # (This will be swapped to the GStreamer Zero-Copy pipeline later for the Jetson Nano)
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FPS, fps)
    
    print("Starting rPPG Pipeline... Waiting for buffer to fill.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # --- 2. Data Pre-processing & ROI Extraction ---
        # Returns a single numerical value (green channel spatial average)
        spatial_avg = preprocessor.extract_green_trace(frame)
        
        if spatial_avg is not None:
            raw_signal_buffer.append(spatial_avg)
            
            # Draw a visual indicator that face is detected
            cv2.putText(frame, "Tracking Face...", (30, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            cv2.putText(frame, "No Face Detected", (30, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # --- 3. Pipeline Execution (Triggers only when window is full) ---
        if len(raw_signal_buffer) == buffer_size:
            raw_signal = np.array(raw_signal_buffer)
            
            dwt_denoised = sig_filter.dwt_denoise(raw_signal)
            filtered_signal = sig_filter.dual_stage_bandpass(dwt_denoised)
            
            # --- Dual-Domain HR Estimation & Weighted Fusion (Paper Stage 4) ---
            hr_time = estimator.estimate_time_domain(filtered_signal)
            hr_freq = estimator.estimate_frequency_domain(filtered_signal)
            sq_time, sq_freq, sq_k = estimator.compute_signal_quality_components(filtered_signal)
            
            # Quality-weighted fusion: higher SQ domain gets more weight
            z_k = estimator.weighted_fusion(hr_time, hr_freq, sq_time, sq_freq)
            
            if z_k is not None:
                final_hr = rakf.update(z_k=z_k, sq_k=sq_k)
                
                # --- 4. Dashboard / UI Output ---
                cv2.putText(frame, f"BPM: {int(final_hr)}", (30, 80), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)

        # Display the output
        cv2.imshow('PatientWatch - Base rPPG Pipeline', frame)
        
        # Press 'q' to gracefully exit the volatile loop
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()