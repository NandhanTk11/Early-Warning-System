# Analysis: Research Paper vs. Codebase Implementation

## Paper Summary

The paper proposes a **DWT-RAKF** framework for remote photoplethysmography (rPPG) heart rate estimation. The pipeline has **four stages**:

1. **Data Pre-processing & ROI Extraction** — CLAHE → Haar cascade face detection → Forehead + Cheek ROIs → Green channel spatial averaging
2. **DWT Denoising** — Wavelet decomposition → MAD-based universal thresholding → Soft shrinkage → IDWT reconstruction
3. **Dual-Stage Bandpass Filtering** — Wide (0.6–3.5 Hz) → Narrow (0.8–2.5 Hz) Butterworth filters, then FFT to produce initial observation $z_k$
4. **RAKF** — Outlier handling → Prediction → Residual → Adaptive $R_k$ → Kalman gain → SQ-weighted state update → Covariance update
5. **HR Estimation** — Dual-domain (time-domain peaks + frequency-domain FFT) → Quality-weighted fusion

Key paper hyperparameters: $Q_k = 2 \times 10^{-4}$, $R_0 = 25$, $\beta > 0$, $\alpha \in [0.1, 0.6]$, $\text{SQ}_k = 0.3 \cdot \text{SPR} + 0.4 \cdot \text{SNR} + 0.3 \cdot \text{PS}$

---

## ✅ What the Code Gets RIGHT

| Component | Paper Requirement | Code Status |
|---|---|---|
| CLAHE enhancement | Applied per-frame on grayscale | ✅ [`preprocessing.py:7,12-13`](file:///d:/Projects/Main Project/rppg_base_pipeline/preprocessing.py#L7-L13) |
| Haar cascade face detection | Haar feature-based cascade classifier | ✅ [`preprocessing.py:6,14`](file:///d:/Projects/Main Project/rppg_base_pipeline/preprocessing.py#L6-L14) |
| 3-ROI extraction (forehead, left cheek, right cheek) | Dynamic ROI selection from face boundary | ✅ [`preprocessing.py:32-34`](file:///d:/Projects/Main Project/rppg_base_pipeline/preprocessing.py#L32-L34) |
| Green channel spatial averaging | Mean of green pixel intensities across ROIs | ✅ [`preprocessing.py:37-42`](file:///d:/Projects/Main Project/rppg_base_pipeline/preprocessing.py#L37-L42) |
| DWT decomposition with `db4` wavelet | Multi-resolution wavelet decomposition | ✅ [`filtering.py:16`](file:///d:/Projects/Main Project/rppg_base_pipeline/filtering.py#L16) |
| MAD-based noise variance estimation | $\sigma = \text{MAD} / 0.6745$ from finest detail coeffs | ✅ [`filtering.py:20-22`](file:///d:/Projects/Main Project/rppg_base_pipeline/filtering.py#L20-L22) |
| Universal threshold $T = \sigma\sqrt{2\log n}$ | Donoho & Johnstone rule | ✅ [`filtering.py:25-26`](file:///d:/Projects/Main Project/rppg_base_pipeline/filtering.py#L25-L26) |
| Soft thresholding on detail coefficients only | Approximation coefficients preserved | ✅ [`filtering.py:30-34`](file:///d:/Projects/Main Project/rppg_base_pipeline/filtering.py#L30-L34) |
| IDWT reconstruction | `pywt.waverec` | ✅ [`filtering.py:37`](file:///d:/Projects/Main Project/rppg_base_pipeline/filtering.py#L37) |
| Stage 1: Wide bandpass 0.6–3.5 Hz | Butterworth filter, `filtfilt` | ✅ [`filtering.py:49-54`](file:///d:/Projects/Main Project/rppg_base_pipeline/filtering.py#L49-L54) |
| Stage 2: Narrow bandpass 0.8–2.5 Hz | Butterworth filter, `filtfilt` | ✅ [`filtering.py:57-61`](file:///d:/Projects/Main Project/rppg_base_pipeline/filtering.py#L57-L61) |
| RAKF prediction step | $\hat{x}_k^- = \hat{x}_{k-1}$, $P_k^- = P_{k-1} + Q_k$ | ✅ [`rakf.py:33-34`](file:///d:/Projects/Main Project/rppg_base_pipeline/rakf.py#L33-L34) |
| Residual computation | $\tilde{y}_k = z_k - \hat{x}_k^-$ | ✅ [`rakf.py:38`](file:///d:/Projects/Main Project/rppg_base_pipeline/rakf.py#L38) |
| Adaptive $R_k$ | $R_0(1 + \|\tilde{y}_k\| / \beta)$ | ✅ [`rakf.py:42`](file:///d:/Projects/Main Project/rppg_base_pipeline/rakf.py#L42) |
| Kalman gain | $K_k = P_k^- / (P_k^- + R_k^{\text{adaptive}})$ | ✅ [`rakf.py:45`](file:///d:/Projects/Main Project/rppg_base_pipeline/rakf.py#L45) |
| SQ-weighted state update | $\hat{x}_k = \hat{x}_k^- + K_k \cdot w_k \cdot \tilde{y}_k$ | ✅ [`rakf.py:52`](file:///d:/Projects/Main Project/rppg_base_pipeline/rakf.py#L52) |
| Covariance update (without $w_k$) | $P_k = (1 - K_k)P_k^-$ | ✅ [`rakf.py:56`](file:///d:/Projects/Main Project/rppg_base_pipeline/rakf.py#L56) |
| Outlier handling via local median | Replace outlier with median of history window | ✅ [`rakf.py:26-28`](file:///d:/Projects/Main Project/rppg_base_pipeline/rakf.py#L26-L28) |
| Time-domain IBI peak detection | `find_peaks` with distance/prominence | ✅ [`hr_estimation.py:10-32`](file:///d:/Projects/Main Project/rppg_base_pipeline/hr_estimation.py#L10-L32) |
| Frequency-domain FFT estimation | FFT → dominant peak in physiological band | ✅ [`hr_estimation.py:34-49`](file:///d:/Projects/Main Project/rppg_base_pipeline/hr_estimation.py#L34-L49) |
| Weighted fusion scheme | Quality-weighted combination of both domains | ✅ [`hr_estimation.py:101-109`](file:///d:/Projects/Main Project/rppg_base_pipeline/hr_estimation.py#L101-L109) |

---

## ⚠️ Deviations from the Paper (Methodology Issues)

### 1. **CRITICAL: `alpha` set to 0.8 — Paper says 0.1–0.6**

> [!CAUTION]
> **Paper (Section: Sensitivity Analysis, Fig 7):** *"the performance remains stable between 0.1 to 0.6 but model performance degrades progressively beyond α = 0.7"*
>
> **Code:** [`rakf.py:5`](file:///d:/Projects/Main Project/rppg_base_pipeline/rakf.py#L5) sets `alpha=0.8`

With `alpha = 0.8`, `w_k = max(0.8, SQ_k)` means the dynamic weighting **almost never activates** — the weight is clamped to 0.8 for all but the cleanest frames, effectively disabling the SQ-based moderation that is the core novelty of the paper. The paper explicitly shows performance degradation beyond 0.7.

**Fix:** Change `alpha` to a value in the range `[0.3, 0.5]` (paper's optimal range).

---

### 2. **CRITICAL: SQ weights deviate from paper**

> [!WARNING]
> **Paper (Eq. 19):** $\text{SQ}_k = 0.3 \cdot \text{SPR} + 0.4 \cdot \text{SNR} + 0.3 \cdot \text{PS}$ (λ₁=0.3, λ₂=0.4, λ₃=0.3)
>
> **Code:** [`hr_estimation.py:96`](file:///d:/Projects/Main Project/rppg_base_pipeline/hr_estimation.py#L96) uses `(0.4 * spr) + (0.4 * norm_snr) + (0.2 * ps)`

The paper explicitly states λ₁=0.3, λ₂=0.4, λ₃=0.3 and notes "SNR values are assigned with higher weights because frequency-domain characteristics are more discriminative." The code increases SPR weight to 0.4 and reduces PS weight to 0.2, which changes the SQ index behavior.

**Fix:** Change to `(0.3 * spr) + (0.4 * norm_snr) + (0.3 * ps)`

---

### 3. **IMPORTANT: Frequency-domain search band narrowed beyond paper spec**

> [!WARNING]
> **Paper:** The physiological frequency range for spectral peak detection is stated as **0.75–2.5 Hz** (45–150 BPM).
>
> **Code:** [`hr_estimation.py:41`](file:///d:/Projects/Main Project/rppg_base_pipeline/hr_estimation.py#L41) uses `frequencies >= 1.1` (i.e., **1.1–2.5 Hz** = 66–150 BPM)

This means any heart rate **below 66 BPM** will be missed by the FFT estimator. Resting heart rates for many adults are 60–65 BPM, so this is a significant restriction that would inflate MAE for subjects at rest.

**Fix:** Change `1.1` to `0.75` to match the paper: `np.where((frequencies >= 0.75) & (frequencies <= self.max_hz))`

---

### 4. **MODERATE: `main.py` does NOT use the dual-domain weighted fusion**

> [!IMPORTANT]
> **Paper:** *"These two complementary estimates from time-domain and spectral-domain are then combined using a weighted fusion scheme."*
>
> **Code:** Both [`main.py:60`](file:///d:/Projects/Main Project/rppg_base_pipeline/main.py#L60) and [`benchmark_pure.py:85`](file:///d:/Projects/Main Project/rppg_base_pipeline/benchmark_pure.py#L85) only call `estimate_frequency_domain()`. The `estimate_time_domain()` and `weighted_fusion()` methods exist but are **never called**.

The paper's Stage 4 (Dual-Domain Estimation & Weighted Fusion) explicitly merges time-domain and frequency-domain estimates using SQ-weighted fusion. This is skipped entirely.

**Fix:** Call both estimators and fuse:
```python
hr_time = estimator.estimate_time_domain(filtered_signal)
hr_freq = estimator.estimate_frequency_domain(filtered_signal)
sq_k = estimator.compute_signal_quality(filtered_signal)

# Use weighted fusion as per paper
z_k = estimator.weighted_fusion(hr_time, hr_freq, sq_k, sq_k)
if z_k is not None:
    final_hr = rakf.update(z_k=z_k, sq_k=sq_k)
```

---

### 5. **MODERATE: Sub-ROI segmentation is NOT implemented**

> [!NOTE]
> **Paper:** *"the detected ROIs are divided into multiple smaller sub-ROIs to reduce the impact of uneven illumination and facial expression"*
>
> **Code:** [`preprocessing.py:32-34`](file:///d:/Projects/Main Project/rppg_base_pipeline/preprocessing.py#L32-L34) extracts 3 ROIs (forehead, left cheek, right cheek) and immediately flattens and averages all pixels. No sub-ROI grid division is performed.

The paper subdivides each ROI into a grid of smaller regions and computes per-sub-ROI averages to mitigate non-uniform illumination. The code just computes a single spatial average per ROI. This could affect robustness under uneven lighting but is not a critical error for basic functionality.

---

### 6. **MINOR: `T_out` threshold value is 30.0 — Paper suggests σ-based**

> [!NOTE]
> **Paper:** *"outlier rejection threshold $T_\text{out}$ is set based on standard deviations of median-filtered residuals"*
>
> **Code:** [`rakf.py:5`](file:///d:/Projects/Main Project/rppg_base_pipeline/rakf.py#L5) uses a hardcoded `t_out=30.0`

The paper implies $T_\text{out}$ should be dynamically computed from the statistics of the residual history, not a fixed constant. However, for most practical purposes, a fixed value may work acceptably.

---

## 🐛 Bugs and Code Issues

### Bug 1: Benchmark computes SQ on the wrong frequency band

The `compute_signal_quality()` method at [`hr_estimation.py:56`](file:///d:/Projects/Main Project/rppg_base_pipeline/hr_estimation.py#L56) uses `self.min_hz = 0.75` for the SQ computation band, but `estimate_frequency_domain()` at [`hr_estimation.py:41`](file:///d:/Projects/Main Project/rppg_base_pipeline/hr_estimation.py#L41) uses `1.1 Hz`. This means the SQ index evaluates quality over a wider band than the HR estimator actually searches, potentially reporting misleading quality scores.

**Fix:** Both methods should use the same frequency band.

---

### Bug 2: Ground-truth alignment issue in `benchmark_pure.py`

[`benchmark_pure.py:92-94`](file:///d:/Projects/Main Project/rppg_base_pipeline/benchmark_pure.py#L92-L94):
```python
if frame_index < len(gt_hr_list):
    predicted_hrs.append(final_hr)
    aligned_gt_hrs.append(gt_hr_list[frame_index])
```

The prediction is appended when `frame_index` is the raw video frame counter, but predictions only start after buffer fills (frame ≥ 300). The ground truth at `gt_hr_list[frame_index]` corresponds to the **current frame** which is correct for alignment, BUT:
- If the face is not detected for some frames, `frame_index` increments but no prediction is made. This means predictions are sparser than ground truth but are aligned by frame index.
- This is **correct alignment** but produces fewer comparisons than possible.

---

### Bug 3: The benchmark loads UBFC format but the file/variable naming suggests PURE dataset

[`benchmark_pure.py:13`](file:///d:/Projects/Main Project/rppg_base_pipeline/benchmark_pure.py#L13) — The function is called `load_ground_truth_ubfc()` and parses the second row of a text file. This is the **UBFC-rPPG** ground truth format (Row 0 = timestamps, Row 1 = HR values).

However, the filename is `benchmark_pure.py` and the paper evaluates on the **PURE** dataset. The PURE dataset uses a different format (JSON files per subject, not text rows). If you're actually benchmarking against UBFC data, the function is correct but the naming is confusing. If you're benchmarking against PURE data, the parser is wrong.

> [!IMPORTANT]
> Verify which dataset `vid.avi` and `ground_truth.txt` actually belong to. If it's UBFC, the parser is correct. If it's PURE, you need a JSON parser.

---

### Bug 4: Missing `peak_width` constraint in `find_peaks`

**Paper:** *"peaks are defined based on the accepted conventions with regard to distance, prominence, and width"*

**Code:** [`hr_estimation.py:21`](file:///d:/Projects/Main Project/rppg_base_pipeline/hr_estimation.py#L21) uses only `distance` and `prominence` but NOT `width`. Adding `width` could help reject false peaks from motion artifacts.

---

### Bug 5: Duplicate comments in `benchmark_pure.py`

[Lines 51-52](file:///d:/Projects/Main Project/rppg_base_pipeline/benchmark_pure.py#L51-L52), [Lines 77-78](file:///d:/Projects/Main Project/rppg_base_pipeline/benchmark_pure.py#L77-L78), and [Lines 103-104](file:///d:/Projects/Main Project/rppg_base_pipeline/benchmark_pure.py#L103-L104) have duplicated comments. These are cosmetic but should be cleaned up.

---

## Summary Table

| # | Issue | Severity | Type | File |
|---|---|---|---|---|
| 1 | `alpha=0.8` exceeds paper's recommended max of 0.6 | 🔴 Critical | Methodology | [`rakf.py:5`](file:///d:/Projects/Main Project/rppg_base_pipeline/rakf.py#L5) |
| 2 | SQ weights differ from paper (0.4/0.4/0.2 vs 0.3/0.4/0.3) | 🔴 Critical | Methodology | [`hr_estimation.py:96`](file:///d:/Projects/Main Project/rppg_base_pipeline/hr_estimation.py#L96) |
| 3 | FFT search band starts at 1.1 Hz, paper says 0.75 Hz | 🟠 Important | Methodology | [`hr_estimation.py:41`](file:///d:/Projects/Main Project/rppg_base_pipeline/hr_estimation.py#L41) |
| 4 | Dual-domain weighted fusion never used in pipeline | 🟠 Important | Missing Feature | [`main.py`](file:///d:/Projects/Main Project/rppg_base_pipeline/main.py), [`benchmark_pure.py`](file:///d:/Projects/Main Project/rppg_base_pipeline/benchmark_pure.py) |
| 5 | Sub-ROI segmentation not implemented | 🟡 Moderate | Missing Feature | [`preprocessing.py`](file:///d:/Projects/Main Project/rppg_base_pipeline/preprocessing.py) |
| 6 | `T_out` hardcoded instead of σ-based | 🟢 Minor | Methodology | [`rakf.py:5`](file:///d:/Projects/Main Project/rppg_base_pipeline/rakf.py#L5) |
| 7 | SQ and FFT use inconsistent frequency bands | 🟠 Bug | Logic | [`hr_estimation.py`](file:///d:/Projects/Main Project/rppg_base_pipeline/hr_estimation.py) |
| 8 | File/function named "UBFC" but benchmark titled "PURE" | 🟡 Bug | Naming | [`benchmark_pure.py`](file:///d:/Projects/Main Project/rppg_base_pipeline/benchmark_pure.py) |
| 9 | Missing `width` param in `find_peaks` | 🟢 Minor | Methodology | [`hr_estimation.py:21`](file:///d:/Projects/Main Project/rppg_base_pipeline/hr_estimation.py#L21) |
| 10 | Duplicate comments | 🟢 Cosmetic | Style | [`benchmark_pure.py`](file:///d:/Projects/Main Project/rppg_base_pipeline/benchmark_pure.py) |

---

## Overall Verdict

**The core architecture is solid and faithfully implements the paper's pipeline structure.** The DWT denoising, dual-stage bandpass filtering, and RAKF state equations are all correctly transcribed from the mathematical formulations. The main concerns are:

1. **Hyperparameter deviations** (alpha, SQ weights, frequency band) that directly contradict the paper's stated values and sensitivity analysis
2. **Missing the dual-domain weighted fusion** — this is a stated contribution of the paper but is not wired into the running pipeline
3. **Inconsistent frequency bands** between the HR estimator and SQ calculator creating a subtle mismatch
