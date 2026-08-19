import joblib

import camera_to_angle as cta
from cmac import CMAC3
from cmac_warmup import warmup

N_CENTERS = 9
TIME_OF_FLIGHT = 0.8   # seconds -- fixed estimate of ball flight time, tune on the robot
WARMUP_DURATION = 30.0  # seconds of prediction-only CMAC warm-up before throwing


def main():
    model = joblib.load(cta.MODEL_PATH)

    cta.initialize_camera()
    cta.initialize_robot()

    x_scaler = model["x_scaler"]
    cmac = CMAC3(n_centers=N_CENTERS, input_range=(x_scaler["lo"], x_scaler["hi"]))

    window = warmup(cmac, cta.wait_for_target_x, TIME_OF_FLIGHT, WARMUP_DURATION)

    while True:
        command = cta.wait_for_next_throw_command()
        if command == "q":
            break

        x1, x2, x3 = window
        x_hat, B = cmac.predict(x1, x2, x3)

        angle_x, y_backswing, y_release = cta.predict_throw(x_hat, model)
        landing_x = cta.throw_and_measure(angle_x, y_backswing, y_release)

        x_true = cta.wait_for_target_x()
        error = x_true - x_hat
        cmac.update(B, error)

        landing_msg = "no crossing detected" if landing_x is None else f"landing_x={landing_x:.1f}"
        print(f"predicted_x={x_hat:.1f} true_x={x_true:.1f} prediction_error={error:+.1f} {landing_msg}")

        window = [x2, x3, x_true]


if __name__ == "__main__":
    main()
