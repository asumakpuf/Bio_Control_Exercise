"""
One-off calibration: determines the sign of d(landing_x)/d(angle_x) on the real
robot, so the PD controller's error convention (x_target - landing_x vs.
landing_x - x_target -- see main.py vs. throw_at_target.py) can be picked from
a measurement instead of guessed.

Throws twice at the same target position -- once with the NN's predicted
angle_x, once with angle_x + DELTA_DEG -- and compares the two landing_x
readings. Keep the target roughly still for the ~10s this takes; a moving
target would confound the comparison.
"""
import joblib
import numpy as np

import camera_to_angle as cta

DELTA_DEG = 5.0  # angle_x offset for the second throw, degrees


def main():
    model = joblib.load(cta.MODEL_PATH)
    cta.initialize_camera()
    cta.initialize_robot()
    cta.go_to_rest()

    x_target = cta.get_target_x()
    print(f"Target at x={x_target:.1f} -- keep it still for this test.")

    angle_x, y_backswing, y_release = cta.predict_throw(x_target, model)
    print(f"\nThrow 1: angle_x={angle_x:.1f}")
    landing_1 = cta.throw_and_measure(
        angle_x, y_backswing, y_release, landing_fn=cta.wait_for_landing_x_tracked
    )
    cta.go_to_rest()
    print(f"landing_x_1={landing_1}")

    angle_x_2 = float(np.clip(angle_x + DELTA_DEG, cta.ANGLE_X_MIN, cta.ANGLE_X_MAX))
    print(f"\nThrow 2: angle_x={angle_x_2:.1f} (angle_x_1 {DELTA_DEG:+.1f})")
    landing_2 = cta.throw_and_measure(
        angle_x_2, y_backswing, y_release, landing_fn=cta.wait_for_landing_x_tracked
    )
    cta.go_to_rest()
    print(f"landing_x_2={landing_2}")

    if landing_1 is None or landing_2 is None:
        print("\nCould not detect a landing on both throws -- rerun the test.")
        return

    d_angle = angle_x_2 - angle_x
    k = (landing_2 - landing_1) / d_angle
    print(f"\nd(landing_x)/d(angle_x) ~= {k:+.2f} px/deg")

    if k > 0:
        print("k > 0: increasing angle_x moves the landing in +x.")
        print("Use error = x_target - landing_x (throw_at_target.py's current convention) in BOTH scripts.")
    else:
        print("k < 0: increasing angle_x moves the landing in -x.")
        print("Use error = landing_x - x_target (main.py's current convention) in BOTH scripts.")


if __name__ == "__main__":
    main()
