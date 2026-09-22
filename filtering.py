import numpy as np
import pywt
from scipy.signal import butter, filtfilt
from scipy.stats import median_abs_deviation

class SignalFilter:
    def __init__(self, fps=30):
        self.fps = fps

    def dwt_denoise(self, signal, wavelet='db4', level=4):
        """
        Applies Discrete Wavelet Transform (DWT) to suppress high-frequency noise 
        while preserving cardiac pulse waveforms.
        """
        # Step 1: Decompose the signal into multi-resolution wavelet coefficients
        coeffs = pywt.wavedec(signal, wavelet, level=level)
        
        # Step 2: Estimate noise variance (sigma) using Median Absolute Deviation (MAD) 
        # from the finest-scale detail coefficients (coeffs[-1])
        detail_coeffs = coeffs[-1]
        mad = median_abs_deviation(detail_coeffs)
        sigma = mad / 0.6745 # Standard conversion factor for Gaussian noise
        
        # Step 3: Calculate Donoho and Johnstone's Universal Threshold (T = sigma * sqrt(2 * log(n)))
        n = len(signal)
        threshold = sigma * np.sqrt(2 * np.log(n))
        
        # Step 4: Soft Thresholding (Coefficient Shrinkage)
        # Apply the threshold to all detail coefficients (skip the approximation coefficients at index 0)
        denoised_coeffs = [coeffs[0]]
        for detail in coeffs[1:]:
            # pywt.threshold applies the mathematical shrinkage: sgn(d) * (|d| - T)
            shrunk_detail = pywt.threshold(detail, value=threshold, mode='soft')
            denoised_coeffs.append(shrunk_detail)
            
        # Step 5: Signal Reconstruction via Inverse DWT
        denoised_signal = pywt.waverec(denoised_coeffs, wavelet)
        
        # Ensure reconstructed signal matches original length (handling odd/even boundaries)
        return denoised_signal[:n]

    def dual_stage_bandpass(self, signal):
        nyquist = 0.5 * self.fps
        
        # MEAN CENTER the signal to prevent massive ringing artifacts at the window edges
        signal = signal - np.mean(signal)
        
        # --- Stage 1: Wide Bandpass Filter (0.6 Hz to 3.5 Hz) ---
        low_wide = 0.6 / nyquist
        high_wide = 3.5 / nyquist
        b_wide, a_wide = butter(N=4, Wn=[low_wide, high_wide], btype='band')
        
        # Use filtfilt for zero-phase forward-backward filtering
        stage1_filtered = filtfilt(b_wide, a_wide, signal)
        
        # --- Stage 2: Narrow Bandpass Filter (0.8 Hz to 2.5 Hz) ---
        low_narrow = 0.8 / nyquist
        high_narrow = 2.5 / nyquist
        b_narrow, a_narrow = butter(N=4, Wn=[low_narrow, high_narrow], btype='band')
        
        stage2_filtered = filtfilt(b_narrow, a_narrow, stage1_filtered)
        
        return stage2_filtered