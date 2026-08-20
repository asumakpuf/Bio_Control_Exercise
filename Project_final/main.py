import argparse
import time

import joblib
import numpy as np

import camera_to_angle as cta
from cmac import CMAC3, DEFAULT_WEIGHTS_PATH, padded_input_range
from cmac_warmup import warmup, sample_window
from config import N_CENTERS, TIME_OF_FLIGHT, WARMUP_DURATION, POLL_INTERVAL
from reporting import plot_prediction, report_learning


def parse_args():
    parser = argparse.ArgumentParser(description="Warm up (or load) a CMAC and throw at a moving target.")
    parser.add_argument(
        "--no-warmup", action="store_true",
        help=f"Skip the in-line CMAC warm-up and load previously trained weights from "
             f"{DEFAULT_WEIGHTS_PATH} instead (see train_cmac.py)."
    )
    parser.add_argument(
        "--no-update", action="store_true",
        help="Predict during live throws but don't call cmac.update() -- weights stay "
             "frozen at whatever they were after warm-up/loading. Use this to test/verify "
             "live predictions and timing without risking corrupting the trained weights "
             "with a still-mistimed x3-to-x_true horizon."
    )
    return parser.parse_args()


def main():
    args = parse_args()
    model = joblib.load(cta.MODEL_PATH)

    cta.initialize_camera()
    cta.initialize_robot()

    x_scaler = model["x_scaler"]

    start_time = time.time()
    if args.no_warmup:
        cmac = CMAC3.load(DEFAULT_WEIGHTS_PATH)
        print(f"Loaded pretrained CMAC weights from {DEFAULT_WEIGHTS_PATH}")

        trained_tof = getattr(cmac, "trained_time_of_flight", None)
        trained_poll = getattr(cmac, "trained_poll_interval", None)
        if trained_tof is None:
            print("  WARNING: these weights predate the trained_time_of_flight check -- "
                  "can't verify they match the current config. Consider retraining with train_cmac.py.")
        elif not np.isclose(trained_tof, TIME_OF_FLIGHT) or not np.isclose(trained_poll, POLL_INTERVAL):
            print(f"  WARNING: these weights were trained with TIME_OF_FLIGHT={trained_tof}s, "
                  f"POLL_INTERVAL={trained_poll}s, but config.py currently has "
                  f"TIME_OF_FLIGHT={TIME_OF_FLIGHT}s, POLL_INTERVAL={POLL_INTERVAL}s. "
                  f"Predictions will be systematically off until you retrain (train_cmac.py) "
                  f"or fix config.py to match.")

        times, y_true, y_pred = [], [], []
    else:
        cmac = CMAC3(n_centers=N_CENTERS, input_range=padded_input_range(x_scaler["lo"], x_scaler["hi"], N_CENTERS))
        _, times, y_true, y_pred = warmup(
            cmac, cta.wait_for_target_x, TIME_OF_FLIGHT, WARMUP_DURATION,
            poll_interval=POLL_INTERVAL, start_time=start_time
        )
        report_learning(y_true, y_pred)

    landing_errors = []
    while True:
        command = cta.wait_for_next_throw_command()
        if command in ("q", "f"):
            break

        window = sample_window(cta.wait_for_target_x, POLL_INTERVAL)
        x3_time = time.time()  # x3 was just sampled -- reference point for the x3->x_true horizon
        x1, x2, x3 = window
        x_hat, B = cmac.predict(x1, x2, x3)

        angle_x, y_backswing, y_release = cta.predict_throw(x_hat, model)
        landing_x = cta.throw_and_measure(angle_x, y_backswing, y_release)

        # throw_and_measure() usually finishes faster than TIME_OF_FLIGHT (that's the
        # budget it was trimmed to fit) -- pad out whatever's left so x_true always
        # lands right at the TIME_OF_FLIGHT mark instead of wherever this particular
        # throw happened to finish. If it ever runs long, there's nothing to pad and
        # horizon_elapsed below will show it.
        remaining = TIME_OF_FLIGHT - (time.time() - x3_time)
        if remaining > 0:
            time.sleep(remaining)

        x_true = cta.wait_for_target_x()
        horizon_elapsed = time.time() - x3_time  # actual x3->x_true gap, vs. assumed TIME_OF_FLIGHT
        error = x_true - x_hat
        if not args.no_update:
            cmac.update(B, error)

        times.append(time.time() - start_time)
        y_true.append(x_true)
        y_pred.append(x_hat)
        if landing_x is not None:
            landing_errors.append(landing_x - x_true)

        landing_msg = "no crossing detected" if landing_x is None else f"landing_x={landing_x:.1f}"
        update_msg = "weights frozen" if args.no_update else "weights updated"
        print(f"window=({x1:.1f}, {x2:.1f}, {x3:.1f}) "
              f"predicted_x={x_hat:.1f} true_x={x_true:.1f} prediction_error={error:+.1f} "
              f"horizon_elapsed={horizon_elapsed:.2f}s (TIME_OF_FLIGHT={TIME_OF_FLIGHT:.2f}s) "
              f"{landing_msg} {update_msg}")
        cta.go_to_rest()  # start parked in the base position, not wherever throw_and_measure left it

    report_learning(y_true, y_pred)
    if landing_errors:
        print(f"Mean absolute landing error: {np.mean(np.abs(landing_errors)):.1f}px over {len(landing_errors)} throws")

    plot_prediction(times, y_true, y_pred)


if __name__ == "__main__":
    main()
