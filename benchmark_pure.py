import cv2
import numpy as np
import json
import math
from collections import deque
import os
import glob

# Import your existing pipeline modules
from preprocessing import Preprocessor
from filtering import SignalFilter
from rakf import RAKF
from hr_estimation import HREstimator

def load_ground_truth_pure(json_path, fps=30):
    """
    Parses the PURE dataset ground truth JSON file.
    The GT is sampled at ~57 Hz; this function downsamples it to match
    the video frame rate by selecting the nearest GT entry per frame.
    Returns one GT HR value per video frame.
    """
    with open(json_path, 'r') as file:
        data = json.load(file)
        
    # PURE dataset structure — the top-level key is "/FullPackage"
    hr_key = "/FullPackage"
    if hr_key not in data or len(data[hr_key]) == 0:
        return []
    
    entries = data[hr_key]
    timestamps = [e["Timestamp"] for e in entries]
    pulse_rates = [float(e["Value"]["pulseRate"]) for e in entries]
    
    # Downsample: select one GT value per video frame interval
    t_start = timestamps[0]
    t_end = timestamps[-1]
    frame_duration_ns = 1e9 / fps  # nanoseconds per frame
    
    gt_hr_per_frame = []
    gt_idx = 0
    frame_time = t_start
    
    while frame_time <= t_end and gt_idx < len(timestamps):
        # Find the GT entry closest to this frame's timestamp
        while gt_idx < len(timestamps) - 1 and timestamps[gt_idx + 1] <= frame_time:
            gt_idx += 1
        gt_hr_per_frame.append(pulse_rates[gt_idx])
        frame_time += frame_duration_ns
    
    return gt_hr_per_frame

def calculate_metrics(predicted_hrs, ground_truth_hrs):
    errors = np.array(predicted_hrs) - np.array(ground_truth_hrs)
    mae = np.mean(np.abs(errors))
    rmse = np.sqrt(np.mean(errors ** 2))
    return mae, rmse

def benchmark_video(video_path, json_path): 
    fps = 30
    window_seconds = 10
    buffer_size = fps * window_seconds  
    
    preprocessor = Preprocessor()
    sig_filter = SignalFilter(fps=fps)
    
    # Paper: alpha=0.3 (optimal per sensitivity analysis), initial_hr=75.0 for resting
    rakf = RAKF(initial_hr=75.0, alpha=0.3) 
    estimator = HREstimator(fps=fps)
    
    raw_signal_buffer = deque(maxlen=buffer_size)
    predicted_hrs = []
    aligned_gt_hrs = []
    
    # Use the new PURE JSON loader
    # Load ground truth
    gt_hr_list = load_ground_truth_pure(json_path)
    if not gt_hr_list:
        print("Error: Could not load ground truth from JSON. Check file structure.")
        return

    # NEW: Read and sort all PNG images in the directory directly
    image_files = sorted(glob.glob(os.path.join(video_path, "*.png")))
    
    if len(image_files) == 0:
        print(f"Error: No PNG images found in {video_path}")
        return

    frame_index = 0
    print(f"Benchmarking started for PURE dataset directory: {video_path}")
    print(f"Found {len(image_files)} images. Processing frames...")

    # Iterate through the sorted image paths instead of using cap.read()
    for img_path in image_files:
        frame = cv2.imread(img_path)
        
        if frame is None:
            print(f"Failed to read {img_path}")
            continue
            
        spatial_avg = preprocessor.extract_green_trace(frame)
        
        if spatial_avg is not None:
            raw_signal_buffer.append(spatial_avg)
            
        if len(raw_signal_buffer) == buffer_size:
            raw_signal = np.array(raw_signal_buffer)
            
            dwt_denoised = sig_filter.dwt_denoise(raw_signal)
            filtered_signal = sig_filter.dual_stage_bandpass(dwt_denoised)
            
            # Paper: Dual-domain HR estimation with weighted fusion
            hr_time = estimator.estimate_time_domain(filtered_signal)
            hr_freq = estimator.estimate_frequency_domain(filtered_signal)
            sq_time, sq_freq, sq_k = estimator.compute_signal_quality_components(filtered_signal)
            z_k = estimator.weighted_fusion(hr_time, hr_freq, sq_time, sq_freq)
            
            if z_k is not None:
                final_hr = rakf.update(z_k=z_k, sq_k=sq_k)
                
                if frame_index < len(gt_hr_list):
                    predicted_hrs.append(final_hr) 
                    aligned_gt_hrs.append(gt_hr_list[frame_index])
                    
                    if len(predicted_hrs) <= 10:
                        print(f"Frame {frame_index} | Time: {hr_time if hr_time else 'N/A':>6} | Freq: {hr_freq if hr_freq else 'N/A':>6} | Fused: {z_k:.2f} | RAKF: {final_hr:.2f} | SQ_k: {sq_k:.2f} | GT: {gt_hr_list[frame_index]}")

        frame_index += 1
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
    # Point directly to the folder containing all the PNG files
    VIDEO_DIR = r"D:\Projects\Main Project\rppg_base_pipeline\02-01" 
    JSON_FILE = r"D:\Projects\Main Project\rppg_base_pipeline\02-01.json" 
    
    # Pass VIDEO_DIR into the function
    benchmark_video(VIDEO_DIR, JSON_FILE)