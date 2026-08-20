import argparse
import time

import joblib
import numpy as np

import camera_to_angle as cta
from cmac import CMAC3, DEFAULT_WEIGHTS_PATH, padded_input_range
from cmac_warmup import warmup, sample_window
from config import N_CENTERS, TIME_OF_FLIGHT, WARMUP_DURATION, POLL_INTERVAL
from pd_controller import PDController
from reporting import plot_prediction, report_learning

# PD trim applied on top of the NN's angle_x prediction (itself computed from the CMAC's
# x_hat), fed by (landing_x - x_target) measured at the moment the ball crosses the
# target's line -- see wait_for_landing_x_and_target_tracked(). Only active with --use-pd.
PD_KP = 0.5  # proportional gain, degrees per pixel of landing error
PD_KD = 0.1  # derivative gain on the change in that error between throws


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
    parser.add_argument(
        "--use-pd", action="store_true",
        help="Trim the NN's angle_x with a PD controller fed by (landing_x - x_target) "
             "from the previous throw, on top of the CMAC's x_hat prediction. Off by "
             "default: the CMAC path already works standalone, so this is opt-in until "
             "PD_KP/PD_KD are tuned on the robot."
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

    pd = PDController(kp=PD_KP, kd=PD_KD) if args.use_pd else None

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
        if pd is not None:
            angle_x = float(np.clip(angle_x + pd.correction, cta.ANGLE_X_MIN, cta.ANGLE_X_MAX))

        # landing_x and x_true come off the SAME frame (the one the crossing was detected
        # on) via wait_for_landing_x_and_target_tracked -- no separate post-hoc camera read
        # or TIME_OF_FLIGHT-padded sleep needed; horizon_elapsed below shows how far the
        # real ball-arrival time actually was from the assumed TIME_OF_FLIGHT.
        landing_x, x_true = cta.throw_and_measure(
            angle_x, y_backswing, y_release,
            landing_fn=cta.wait_for_landing_x_and_target_tracked,
        )
        horizon_elapsed = time.time() - x3_time

        if x_true is not None:
            error = x_true - x_hat
            if not args.no_update:
                cmac.update(B, error)
            times.append(time.time() - start_time)
            y_true.append(x_true)
            y_pred.append(x_hat)
        else:
            error = None

        if pd is not None and landing_x is not None and x_true is not None:
            pd.update(landing_x - x_true)
        if landing_x is not None and x_true is not None:
            landing_errors.append(landing_x - x_true)

        landing_msg = "no crossing detected" if landing_x is None else f"landing_x={landing_x:.1f}"
        update_msg = "weights frozen" if args.no_update else "weights updated"
        pd_msg = "" if pd is None else f" pd_correction={pd.correction:+.2f}"
        error_msg = "n/a (no crossing)" if error is None else f"{error:+.1f}"
        true_x_msg = "n/a" if x_true is None else f"{x_true:.1f}"
        print(f"window=({x1:.1f}, {x2:.1f}, {x3:.1f}) "
              f"predicted_x={x_hat:.1f} true_x={true_x_msg} prediction_error={error_msg} "
              f"horizon_elapsed={horizon_elapsed:.2f}s (TIME_OF_FLIGHT={TIME_OF_FLIGHT:.2f}s) "
              f"{landing_msg} {update_msg}{pd_msg}")
        cta.go_to_rest()  # start parked in the base position, not wherever throw_and_measure left it

    report_learning(y_true, y_pred)
    if landing_errors:
        print(f"Mean absolute landing error: {np.mean(np.abs(landing_errors)):.1f}px over {len(landing_errors)} throws")

    plot_prediction(times, y_true, y_pred)


if __name__ == "__main__":
    main()
