import time

import joblib
import numpy as np
import matplotlib.pyplot as plt

import camera_to_angle as cta
from cmac import CMAC3
from cmac_warmup import warmup

N_CENTERS = 9
TIME_OF_FLIGHT = 3.0   # seconds -- fixed estimate of ball flight time, tune on the robot
WARMUP_DURATION = 60.0  # seconds of prediction-only CMAC warm-up before throwing
POLL_INTERVAL = 0.5    # seconds between buffered target samples during warm-up
                        # (independent of TIME_OF_FLIGHT -- see cmac_warmup.warmup)
MSE_WINDOW = 20         # number of predictions compared first-vs-last in report_learning

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


def main():
    model = joblib.load(cta.MODEL_PATH)

    cta.initialize_camera()
    cta.initialize_robot()

    x_scaler = model["x_scaler"]
    cmac = CMAC3(n_centers=N_CENTERS, input_range=(x_scaler["lo"], x_scaler["hi"]))

    start_time = time.time()
    window, times, y_true, y_pred = warmup(
        cmac, cta.wait_for_target_x, TIME_OF_FLIGHT, WARMUP_DURATION,
        poll_interval=POLL_INTERVAL, start_time=start_time
    )
    report_learning(y_true, y_pred)

    landing_errors = []
    while True:
        command = cta.wait_for_next_throw_command()
        if command in ("q", "f"):
            break

        x1, x2, x3 = window
        x_hat, B = cmac.predict(x1, x2, x3)

        angle_x, y_backswing, y_release = cta.predict_throw(x_hat, model)
        landing_x = cta.throw_and_measure(angle_x, y_backswing, y_release)
        x_true = cta.wait_for_target_x()
        error = x_true - x_hat
        cmac.update(B, error)

        times.append(time.time() - start_time)
        y_true.append(x_true)
        y_pred.append(x_hat)
        if landing_x is not None:
            landing_errors.append(landing_x - x_true)

        landing_msg = "no crossing detected" if landing_x is None else f"landing_x={landing_x:.1f}"
        print(f"predicted_x={x_hat:.1f} true_x={x_true:.1f} prediction_error={error:+.1f} {landing_msg}")

        window = [x2, x3, x_true]

    report_learning(y_true, y_pred)
    if landing_errors:
        print(f"Mean absolute landing error: {np.mean(np.abs(landing_errors)):.1f}px over {len(landing_errors)} throws")

    plot_prediction(times, y_true, y_pred)


if __name__ == "__main__":
    main()
