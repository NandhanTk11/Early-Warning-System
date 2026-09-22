import numpy as np
from collections import deque

class RAKF:
    def __init__(self, initial_hr=100.0, q=2e-4, r0=25.0, beta=10.0, alpha=0.3, t_out=30.0, history_size=10):
        # State variables
        self.x = initial_hr            # x_k: Start closer to expected active HR
        self.P = 1.0                   
        self.Q = q                     
        self.R0 = r0                   
        self.beta = beta               
        self.alpha = alpha             
        self.T_out = t_out             # Expanded outlier threshold to allow high HR jumps
        
        # Initialize history buffer near the target range
        self.z_history = deque([initial_hr] * history_size, maxlen=history_size)

    def update(self, z_k, sq_k):
        """
        Executes one frame-wise cycle of the Adaptive Kalman Filter.
        z_k: The raw HR observation from the camera (e.g., from FFT)
        sq_k: The computed Signal Quality Index (0.0 to 1.0)
        """
        # --- Step 1: Outlier Handling via Local Reference[cite: 3, 4] ---
        # Calculate the median of recent observations to check for massive, sudden glitches
        z_median = np.median(self.z_history)
        if abs(z_k - z_median) > self.T_out:
            z_k = z_median  # Replace outlier with local median[cite: 3, 4]
            
        self.z_history.append(z_k)

        # --- Step 2: Prediction Phase ---
        x_prior = self.x               # x_{k|k-1} = x_{k-1}[cite: 3, 4]
        P_prior = self.P + self.Q      # P_{k|k-1} = P_{k-1} + Q_k[cite: 3, 4]

        # --- Step 3: Residual Computation ---
        # Mathematical difference between camera reading and our prediction
        y_tilde = z_k - x_prior        # \tilde{y}_k = z_k - \hat{x}^-_{k}[cite: 3, 4]

        # --- Step 4: Adaptive Measurement Noise & Kalman Gain ---
        # If residual (y_tilde) is huge, R_adaptive spikes[cite: 3, 4]
        R_adaptive = self.R0 * (1 + (abs(y_tilde) / self.beta))
        
        # Calculate Kalman Gain (K_k). High R_adaptive forces K_k toward 0[cite: 3, 4]
        K_k = P_prior / (P_prior + R_adaptive)

        # --- Step 5: State Update with Dynamic SQ Weighting ---
        # Ensure the weight doesn't drop below the alpha threshold[cite: 3, 4]
        w_k = max(self.alpha, sq_k)
        
        # Final weighted posterior state estimate[cite: 3, 4]
        self.x = x_prior + K_k * w_k * y_tilde

        # --- Step 6: Error Covariance Update ---
        # Note: w_k is excluded here to preserve statistical consistency under Gaussian noise[cite: 3, 4]
        self.P = (1 - K_k) * P_prior

        return self.x