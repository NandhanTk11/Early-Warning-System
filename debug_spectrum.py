"""
Quick diagnostic: Visualize what the FFT spectrum looks like 
after DWT + bandpass filtering. This will show us WHY the FFT 
is picking 73 BPM instead of 100 BPM.
"""
import cv2
import numpy as np
from collections import deque
from preprocessing import Preprocessor
from filtering import SignalFilter

fps = 30
window_seconds = 10
buffer_size = fps * window_seconds

preprocessor = Preprocessor()
sig_filter = SignalFilter(fps=fps)

raw_signal_buffer = deque(maxlen=buffer_size)

cap = cv2.VideoCapture(r"D:\Projects\Main Project\rppg_base_pipeline\vid.avi")
frame_index = 0

print("Extracting signal from first 300 frames...")

while frame_index < buffer_size:
    ret, frame = cap.read()
    if not ret:
        break
    spatial_avg = preprocessor.extract_green_trace(frame)
    if spatial_avg is not None:
        raw_signal_buffer.append(spatial_avg)
    frame_index += 1

cap.release()

if len(raw_signal_buffer) < buffer_size:
    print(f"Warning: Only got {len(raw_signal_buffer)} samples, need {buffer_size}")

raw_signal = np.array(raw_signal_buffer)

# Run through the pipeline stages
dwt_denoised = sig_filter.dwt_denoise(raw_signal)
filtered_signal = sig_filter.dual_stage_bandpass(dwt_denoised)

# --- FFT Analysis ---
n_padded = 2048
spectrum = np.fft.fft(filtered_signal, n=n_padded)
frequencies = np.fft.fftfreq(n_padded, d=1.0/fps)
power = np.abs(spectrum[:n_padded//2]) ** 2
freqs_positive = frequencies[:n_padded//2]

# Convert to BPM
bpm_axis = freqs_positive * 60.0

# Find peaks in the cardiac range
cardiac_mask = (freqs_positive >= 0.5) & (freqs_positive <= 3.5)
cardiac_bpm = bpm_axis[cardiac_mask]
cardiac_power = power[cardiac_mask]

# Find the code's actual search range (1.1 - 2.5 Hz)
code_mask = (freqs_positive >= 1.1) & (freqs_positive <= 2.5)
code_bpm = bpm_axis[code_mask]
code_power = power[code_mask]

dominant_idx = np.argmax(cardiac_power)
dominant_bpm_wide = cardiac_bpm[dominant_idx]

code_dominant_idx = np.argmax(code_power)
dominant_bpm_code = code_bpm[code_dominant_idx]

print(f"\n=== FFT SPECTRUM DIAGNOSTIC ===")
print(f"Raw signal mean: {np.mean(raw_signal):.2f}")
print(f"Raw signal std:  {np.std(raw_signal):.4f}")
print(f"Filtered signal std: {np.std(filtered_signal):.6f}")
print(f"")
print(f"Dominant peak (full cardiac band 0.5-3.5 Hz): {dominant_bpm_wide:.2f} BPM")
print(f"Dominant peak (code's search band 1.1-2.5 Hz):  {dominant_bpm_code:.2f} BPM")
print(f"Ground Truth: 100.0 BPM")
print(f"")

# Show top 5 peaks in the cardiac range
sorted_indices = np.argsort(cardiac_power)[::-1][:5]
print("Top 5 frequency peaks (0.5-3.5 Hz range):")
for i, idx in enumerate(sorted_indices):
    print(f"  #{i+1}: {cardiac_bpm[idx]:.2f} BPM (power: {cardiac_power[idx]:.2f})")

# Also show raw signal stats
print(f"\n=== RAW SIGNAL STATS ===")
print(f"Signal length: {len(raw_signal)} samples")
print(f"Min pixel value: {np.min(raw_signal):.2f}")
print(f"Max pixel value: {np.max(raw_signal):.2f}")
print(f"Range: {np.max(raw_signal) - np.min(raw_signal):.4f}")
print(f"Coefficient of variation: {np.std(raw_signal)/np.mean(raw_signal)*100:.4f}%")

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend - saves to file without blocking
    import matplotlib.pyplot as plt
    
    fig, axes = plt.subplots(4, 1, figsize=(14, 12))
    
    # Plot 1: Raw green trace
    axes[0].plot(raw_signal, color='green', linewidth=0.5)
    axes[0].set_title('Raw Green Channel Spatial Average')
    axes[0].set_xlabel('Frame')
    axes[0].set_ylabel('Pixel Intensity')
    
    # Plot 2: Filtered signal
    axes[1].plot(filtered_signal, color='blue', linewidth=0.5)
    axes[1].set_title('After DWT + Dual-Stage Bandpass')
    axes[1].set_xlabel('Frame')
    axes[1].set_ylabel('Amplitude')
    
    # Plot 3: FFT full cardiac range
    axes[2].plot(cardiac_bpm, cardiac_power, color='navy')
    axes[2].axvline(x=100, color='red', linestyle='--', linewidth=2, label='GT: 100 BPM')
    axes[2].axvline(x=dominant_bpm_wide, color='orange', linestyle='--', linewidth=2, label=f'Peak: {dominant_bpm_wide:.1f} BPM')
    axes[2].set_title('FFT Power Spectrum (Full Cardiac Band: 30-210 BPM)')
    axes[2].set_xlabel('BPM')
    axes[2].set_ylabel('Power')
    axes[2].legend()
    
    # Plot 4: FFT code's search band
    axes[3].plot(code_bpm, code_power, color='darkgreen')
    axes[3].axvline(x=100, color='red', linestyle='--', linewidth=2, label='GT: 100 BPM')
    axes[3].axvline(x=dominant_bpm_code, color='orange', linestyle='--', linewidth=2, label=f'Code picks: {dominant_bpm_code:.1f} BPM')
    axes[3].axvspan(66, 150, alpha=0.1, color='green', label='Code search: 1.1-2.5 Hz')
    axes[3].set_title("FFT Power Spectrum (Code's Search Band: 66-150 BPM)")
    axes[3].set_xlabel('BPM')
    axes[3].set_ylabel('Power')
    axes[3].legend()
    
    plt.tight_layout()
    plt.savefig(r'D:\Projects\Main Project\rppg_base_pipeline\fft_diagnostic.png', dpi=150)
    print("\nPlot saved to fft_diagnostic.png")
    
except ImportError:
    print("\nmatplotlib not installed - skipping plots. Install with: pip install matplotlib")
