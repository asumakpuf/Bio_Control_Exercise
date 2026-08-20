"""
Shared plotting/reporting helpers for CMAC prediction runs -- used by both
train_cmac.py (warm-up only) and main.py (live throwing), so both produce the
same kind of learning-curve plot and MSE summary.
"""
import numpy as np
import matplotlib.pyplot as plt

from config import MSE_WINDOW


def plot_prediction(times, y_true, y_pred):
    """Plot the CMAC's predicted vs. true target trajectory, and the error, over time."""
    times = np.array(times)
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    fig, (ax_traj, ax_err) = plt.subplots(2, 1, figsize=(9, 6), sharex=True)

    ax_traj.plot(times, y_true, label="True", linewidth=2)
    ax_traj.plot(times, y_pred, label="Predicted", linestyle="--")
    ax_traj.set_ylabel("Target x [pixels]")
    ax_traj.set_title("CMAC prediction vs. true target position")
    ax_traj.legend()
    ax_traj.grid(True, alpha=0.3)

    ax_err.plot(times, y_true - y_pred, color="tab:red")
    ax_err.axhline(0, color="black", linewidth=0.8)
    ax_err.set_xlabel("Time [s]")
    ax_err.set_ylabel("Prediction error")
    ax_err.grid(True, alpha=0.3)

    fig.tight_layout()
    plt.show()


def report_learning(y_true, y_pred, window=MSE_WINDOW):
    """Prints MSE over the first vs. last window predictions, to check the CMAC is learning."""
    errors_sq = (np.array(y_true) - np.array(y_pred)) ** 2

    if len(errors_sq) < 2 * window:
        print(f"Not enough samples yet for a first-vs-last MSE comparison (need >= {2 * window}).")
        return

    mse_first = errors_sq[:window].mean()
    mse_last = errors_sq[-window:].mean()
    print(f"MSE first {window} predictions: {mse_first:.2f}")
    print(f"MSE last {window} predictions:  {mse_last:.2f}")
    print("Learning:", "yes" if mse_last < mse_first else "no improvement yet")
