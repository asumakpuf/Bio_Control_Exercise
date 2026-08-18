"""
cmac3.py

A 3-input CMAC (Cerebellar Model Articulation Controller) for predicting
the next position of a moving target from its position at the last 3
time steps.

This follows the same equations as the course material (Exercises 2.5/2.6):

    phi_ki(x_k) = exp( -(x_k - mu_ki)^2 / sigma_k^2 )      (basis functions, per input dim)
    B_ijk       = phi_1i * phi_2j * phi_3k                  (3D activation "grid")
    y_hat       = sum_ijk  w_ijk * B_ijk                    (output)
    w_ijk      += beta * e * B_ijk                          (covariance learning rule)

Only extended from 2 inputs to 3 inputs. Nothing else about the math changes.
"""

import numpy as np


class CMAC3:
    def __init__(self, n_centers=10, input_range=(0.0, 1.0), sigma=None, beta=0.1):
        """
        n_centers : int
            Number of receptive field centers PER input dimension (N in the notes).
            Total number of weights = n_centers ** 3, so keep this modest.
        input_range : (low, high)
            Expected min/max of the target position. Same range is used for
            all 3 input dimensions since they're the same physical quantity
            (position) just at different time steps.
        sigma : float or None
            Width of each Gaussian receptive field. If None, it's set
            automatically to the spacing between adjacent centers, which is
            a sensible default (fields overlap enough to interpolate smoothly).
        beta : float
            Learning rate.
        """
        self.N = n_centers
        self.beta = beta

        low, high = input_range
        # Centers evenly spaced across the expected input range.
        # Same centers are reused for all 3 dimensions (x1, x2, x3 all live
        # in "position space"), but they're stored separately in case you
        # want different ranges per dimension later.
        self.mu = [np.linspace(low, high, self.N) for _ in range(3)]

        if sigma is None:
            spacing = (high - low) / (self.N - 1)
            self.sigma = [spacing for _ in range(3)]
        else:
            self.sigma = [sigma, sigma, sigma]

        # Weight tensor: shape (N, N, N), one weight per grid cell w_ijk
        self.weights = np.zeros((self.N, self.N, self.N))

    def _phi(self, x, dim):
        """
        Compute phi_ki(x) for ALL i at once, for a single input dimension.
        Returns a vector of length N (Eq. 1 / Eq. 2, vectorized).
        """
        mu = self.mu[dim]
        sigma = self.sigma[dim]
        return np.exp(-((x - mu) ** 2) / (sigma ** 2))

    def _activation_grid(self, x1, x2, x3):
        """
        Compute the full 3D activation grid B_ijk (Eq. 3, extended to 3D)
        as an outer product of the three per-dimension activation vectors.
        This avoids an explicit N^3 loop.
        """
        phi1 = self._phi(x1, dim=0)  # shape (N,)
        phi2 = self._phi(x2, dim=1)  # shape (N,)
        phi3 = self._phi(x3, dim=2)  # shape (N,)

        # Outer product across 3 vectors -> shape (N, N, N)
        B = np.einsum('i,j,k->ijk', phi1, phi2, phi3)
        return B

    def predict(self, x1, x2, x3):
        """
        Forward pass (Step 6 in the explanation): given the last 3 positions,
        return the predicted next position y_hat (Eq. 4, extended to 3D).

        Also returns the activation grid B, since it's needed again for the
        weight update (Step 8) and it's wasteful to recompute it.
        """
        B = self._activation_grid(x1, x2, x3)
        y_hat = np.sum(self.weights * B)
        return y_hat, B

    def update(self, B, error):
        """
        Covariance learning rule (Eq. 5, extended to 3D).

        B     : activation grid returned by predict(), for the SAME input
                that produced the prediction being corrected.
        error : y_true - y_hat
        """
        self.weights += self.beta * error * B


def run_demo():
    """
    Minimal demo showing the full online loop:
      - maintain a sliding window of the last 3 positions
      - predict the next position
      - once the true next position is known, compute error and update

    Replace `target_position(t)` with your actual target-tracking data source.
    """

    def target_position(t):
        # Example periodic pattern - replace with your real target signal.
        return np.sin(2 * np.pi * t / 20.0)

    cmac = CMAC3(n_centers=9, input_range=(-1.0, 1.0), beta=0.05)

    # Initialize sliding window with the first 3 known positions (t=0,1,2)
    window = [target_position(0), target_position(1), target_position(2)]

    errors = []
    n_steps = 500

    for t in range(2, 2 + n_steps):
        x1, x2, x3 = window  # positions at t-2, t-1, t

        # Step 6: predict position at t+1
        y_hat, B = cmac.predict(x1, x2, x3)

        # "Wait one time step" -> true position at t+1 becomes available
        y_true = target_position(t + 1)

        # Step 7-8: compute error and update weights
        error = y_true - y_hat
        cmac.update(B, error)
        errors.append(error ** 2)

        # Step 9: slide the window forward
        window = [x2, x3, y_true]

    errors = np.array(errors)
    print(f"Initial MSE (first 20 steps):  {errors[:20].mean():.5f}")
    print(f"Final MSE   (last 20 steps):   {errors[-20:].mean():.5f}")


if __name__ == "__main__":
    run_demo()