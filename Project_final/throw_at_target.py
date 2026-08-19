"""
Loads the trained model, detects the target's current position with the
camera, and throws the ball at it.
"""
import joblib

import camera_to_angle as cta


def get_target_x():
    frame = cta.ct.capture_image(cta._cam)
    target_coordinates = cta.get_target_bounding_box_coordinates(frame, cta._target_model)
    if target_coordinates is None:
        raise RuntimeError("Target not visible in the camera frame.")
    return target_coordinates.center[0]


if __name__ == "__main__":
    model = joblib.load(cta.MODEL_PATH)

    cta.initialize_camera()
    cta.initialize_robot()

    x_target = get_target_x()
    print(f"Target detected at x={x_target:.1f}")

    angle_x, y_backswing, y_release = cta.predict_throw(x_target, model)
    print(f"Predicted throw: angle_x={angle_x:.1f} y_backswing={y_backswing:.1f} y_release={y_release:.1f}")

    landing_x = cta.throw_and_measure(angle_x, y_backswing, y_release)
    if landing_x is None:
        print("Could not detect where the ball landed.")
    else:
        print(f"Ball landed at x={landing_x:.1f} (target was x={x_target:.1f}, error={landing_x - x_target:+.1f}px)")
