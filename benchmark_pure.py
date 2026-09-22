import cv2
import numpy as np
import json
import math
from collections import deque

# Import your existing pipeline modules
from preprocessing import Preprocessor
from filtering import SignalFilter
from rakf import RAKF
from hr_estimation import HREstimator

def load_ground_truth_ubfc(txt_path):
    """
    Parses the UBFC-rPPG ground truth text file.
    Typically, the first row contains the ground truth HR for each frame.
    """
    gt_hr_list = []
    with open(txt_path, 'r') as file:
        lines = file.readlines()
        
    # UBFC ground truth files usually have the HR array as the first line, 
    # separated by spaces.
    # Read the second row (index 1) to get the actual Heart Rate BPM
    hr_data = lines[1].strip().split()
    
    for value in hr_data:
        gt_hr_list.append(float(value))
        
    return gt_hr_list

def calculate_metrics(predicted_hrs, ground_truth_hrs):
    """
    Calculates Mean Absolute Error (MAE) and Root Mean Square Error (RMSE).
    """
    errors = np.array(predicted_hrs) - np.array(ground_truth_hrs)
    
    mae = np.mean(np.abs(errors))
    rmse = np.sqrt(np.mean(errors ** 2))
    
    return mae, rmse

def benchmark_video(video_path, txt_path): # <-- Change 1: Rename argument
    fps = 30
    window_seconds = 10
    buffer_size = fps * window_seconds  
    
    preprocessor = Preprocessor()
    sig_filter = SignalFilter(fps=fps)
    rakf = RAKF(initial_hr=100.0) # <--- UPDATE THIS LINE FROM 75.0 TO 100.0
    estimator = HREstimator(fps=fps)
    
    raw_signal_buffer = deque(maxlen=buffer_size)
    predicted_hrs = []
    aligned_gt_hrs = []
    
    # <-- Change 2: Call the new UBFC function
    gt_hr_list = load_ground_truth_ubfc(txt_path)
    
    cap = cv2.VideoCapture(video_path)
    frame_index = 0
    
    print(f"Benchmarking started for: {video_path}")
    print("Processing frames (this will run fast without visual output)...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break # End of video
            
        spatial_avg = preprocessor.extract_green_trace(frame)
        
        if spatial_avg is not None:
            raw_signal_buffer.append(spatial_avg)
            
        # Pipeline triggers only when the sliding window is completely full
        # Pipeline triggers only when the sliding window is completely full
       # Pipeline triggers only when the sliding window is completely full
        if len(raw_signal_buffer) == buffer_size:
            raw_signal = np.array(raw_signal_buffer)
            
            dwt_denoised = sig_filter.dwt_denoise(raw_signal)
            filtered_signal = sig_filter.dual_stage_bandpass(dwt_denoised)
            
            hr_freq = estimator.estimate_frequency_domain(filtered_signal)
            sq_k = estimator.compute_signal_quality(filtered_signal)
            
            if hr_freq is not None:
                # Single, correct update call
                final_hr = rakf.update(z_k=hr_freq, sq_k=sq_k)
                
                if frame_index < len(gt_hr_list):
                    predicted_hrs.append(final_hr) 
                    aligned_gt_hrs.append(gt_hr_list[frame_index])
                    
                    if len(predicted_hrs) <= 10:
                        print(f"Frame {frame_index} | Raw FFT: {hr_freq:.2f} | RAKF Output: {final_hr:.2f} | SQ_k: {sq_k:.2f} | GT: {gt_hr_list[frame_index]}")

        frame_index += 1

    cap.release()
    
    # Calculate Final Metrics
    # Calculate Final Metrics
    if len(predicted_hrs) > 0:
        print("\n--- DIAGNOSTIC CHECK (FIRST 10 PREDICTIONS) ---")
        for i in range(10):
            if i < len(predicted_hrs):
                print(f"Predicted HR: {predicted_hrs[i]:.2f} BPM  |  Ground Truth: {aligned_gt_hrs[i]:.2f}  |  Diff: {abs(predicted_hrs[i]-aligned_gt_hrs[i]):.2f}")
        print("-----------------------------------------------")
        
        mae, rmse = calculate_metrics(predicted_hrs, aligned_gt_hrs)
        print("\n--- Benchmarking Results ---")
        print(f"Total Frames Processed: {frame_index}")
        print(f"Total Predictions Made: {len(predicted_hrs)}")
        print(f"Mean Absolute Error (MAE): {mae:.2f} BPM")
        print(f"Root Mean Square Error (RMSE): {rmse:.2f} BPM")
    else:
        print("Error: Pipeline failed to generate predictions.")
if __name__ == "__main__":
    # Change these paths to wherever you extract the UBFC dataset
    VIDEO_FILE = r"D:\Projects\Main Project\rppg_base_pipeline\vid.avi"
    TXT_FILE = r"D:\Projects\Main Project\rppg_base_pipeline\ground_truth.txt" # <-- Change 3: Update to .txt
    
    benchmark_video(VIDEO_FILE, TXT_FILE)