import numpy as np
from scipy.signal import find_peaks

class HREstimator:
    def __init__(self, fps=30):
        self.fps = fps
        self.min_hz = 0.75  
        self.max_hz = 2.5   

    def estimate_time_domain(self, signal):
        min_distance_frames = int(self.fps / self.max_hz)
        
        # Prevent division by zero on flatline signals
        if np.std(signal) == 0:
            return None
            
        # Z-SCORE NORMALIZE the signal so amplitude is mathematically invariant to lighting
        norm_signal = (signal - np.mean(signal)) / np.std(signal)
        
        # Prominence of 0.5 now strictly means 'half a standard deviation'
        peaks, _ = find_peaks(norm_signal, distance=min_distance_frames, prominence=0.5)
        
        if len(peaks) < 2:
            return None
            
        intervals = np.diff(peaks) / self.fps
        avg_ibi = np.mean(intervals)
        hr_bpm = (1.0 / avg_ibi) * 60.0
        
        if 45.0 <= hr_bpm <= 150.0:
            return hr_bpm
        return None

    def estimate_frequency_domain(self, signal):
        n_padded = 2048 
        spectrum = np.fft.fft(signal, n=n_padded)
        frequencies = np.fft.fftfreq(n_padded, d=1.0/self.fps)
        
        # RESTRICT SEARCH BAND: Focus between 0.8 Hz (48 BPM) and 2.5 Hz (150 BPM)
        # matching the narrow bandpass filter range (Stage 2)
        valid_idx = np.where((frequencies >= 0.8) & (frequencies <= self.max_hz))[0]
        
        if len(valid_idx) == 0:
            return None
            
        power = np.abs(spectrum[valid_idx]) ** 2
        dominant_freq = frequencies[valid_idx[np.argmax(power)]]
        
        return dominant_freq * 60.0

    # def compute_signal_quality(self, signal):
    #     n_padded = 2048
    #     spectrum = np.fft.fft(signal, n=n_padded)
    #     frequencies = np.fft.fftfreq(n_padded, d=1.0/self.fps)
        
    #     valid_idx = np.where((frequencies >= self.min_hz) & (frequencies <= self.max_hz))[0]
    #     if len(valid_idx) == 0:
    #         return 0.1
            
    #     power = np.abs(spectrum[valid_idx]) ** 2
    #     total_power = np.sum(power)
        
    #     if total_power == 0:
    #         return 0.1
            
    #     peak_idx = np.argmax(power)
    #     window_min = max(0, peak_idx - 10)
    #     window_max = min(len(power), peak_idx + 11)
        
    #     signal_power = np.sum(power[window_min:window_max])
    #     noise_power = total_power - signal_power
        
    #     spr = signal_power / total_power
    #     snr_raw = signal_power / noise_power if noise_power > 0 else 1.0
        
    #     # BOOST: Make norm_snr more sensitive so clean peaks yield high confidence
    #     norm_snr = min(snr_raw / 2.5, 1.0) 
        
    #     # Time Domain Peak Stability (PS)
    #     ps = 0.5 # Default baseline confidence
    #     if np.std(signal) > 0:
    #         norm_signal = (signal - np.mean(signal)) / np.std(signal)
    #         min_distance_frames = int(self.fps / self.max_hz)
    #         from scipy.signal import find_peaks
    #         peaks, _ = find_peaks(norm_signal, distance=min_distance_frames, prominence=0.4)
            
    #         if len(peaks) >= 3:
    #             intervals = np.diff(peaks) / self.fps
    #             mean_ibi = np.mean(intervals)
    #             std_ibi = np.std(intervals)
    #             if mean_ibi > 0:
    #                 cv = std_ibi / mean_ibi
    #                 ps = max(0.2, 1.0 - cv)

    #     # Re-weighted to heavily favor Spectral Power Ratio and SNR for clean frequency tracking
    #     sq_index = (0.4 * spr) + (0.4 * norm_snr) + (0.2 * ps)
        
    #     # CHANGE THIS LINE: Lower the floor so the filter accepts good raw FFTs
    #     return float(min(max(sq_index, 0.1), 1.0))

    def compute_signal_quality_components(self, signal):
        """
        Returns domain-specific quality scores for the weighted fusion scheme.
        - sq_time: driven by Peak Stability (PS) — reliability of time-domain peak detection
        - sq_freq: driven by Spectral Power Ratio (SPR) + SNR — reliability of FFT estimation
        - sq_composite: the overall SQ index used for the RAKF weighting
        """
        n_padded = 2048
        spectrum = np.fft.fft(signal, n=n_padded)
        frequencies = np.fft.fftfreq(n_padded, d=1.0/self.fps)
        
        valid_idx = np.where((frequencies >= self.min_hz) & (frequencies <= self.max_hz))[0]
        if len(valid_idx) == 0:
            return 0.3, 0.3, 0.1
            
        power = np.abs(spectrum[valid_idx]) ** 2
        total_power = np.sum(power)
        
        if total_power == 0:
            return 0.3, 0.3, 0.1
            
        peak_idx = np.argmax(power)
        window_min = max(0, peak_idx - 10)
        window_max = min(len(power), peak_idx + 11)
        
        signal_power = np.sum(power[window_min:window_max])
        noise_power = total_power - signal_power
        
        spr = signal_power / total_power
        snr_raw = signal_power / noise_power if noise_power > 0 else 1.0
        norm_snr = min(snr_raw / 2.5, 1.0)
        
        # Time Domain Peak Stability (PS)
        ps = 0.5
        if np.std(signal) > 0:
            norm_signal = (signal - np.mean(signal)) / np.std(signal)
            min_distance_frames = int(self.fps / self.max_hz)
            peaks, _ = find_peaks(norm_signal, distance=min_distance_frames, prominence=0.4)
            
            if len(peaks) >= 3:
                intervals = np.diff(peaks) / self.fps
                mean_ibi = np.mean(intervals)
                std_ibi = np.std(intervals)
                if mean_ibi > 0:
                    cv = std_ibi / mean_ibi
                    ps = max(0.2, 1.0 - cv)
        
        # Domain-specific quality scores
        sq_time = ps
        sq_freq = (spr + norm_snr) / 2.0
        
        # Overall composite SQ (paper: 0.3*SPR + 0.4*SNR + 0.3*PS)
        sq_composite = (0.3 * spr) + (0.4 * norm_snr) + (0.3 * ps)
        sq_composite = float(min(max(sq_composite, 0.1), 1.0))
        
        return sq_time, sq_freq, sq_composite

    def weighted_fusion(self, hr_time, hr_freq, sq_time, sq_freq):
        if hr_time is None: return hr_freq
        if hr_freq is None: return hr_time
        
        total_sq = sq_time + sq_freq
        w_time = sq_time / total_sq
        w_freq = sq_freq / total_sq
        
        return (w_time * hr_time) + (w_freq * hr_freq)