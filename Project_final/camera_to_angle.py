import sys
import time
from pathlib import Path

import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import train_test_split
import joblib
import matplotlib.pyplot as plt

import camera_tools as ct
from FableAPI.fable_init import api

for _parent in Path(__file__).resolve().parents:
    _candidate = _parent / "biggest_white_object_tracker"
    if _candidate.is_dir():
        if str(_candidate) not in sys.path:
            sys.path.insert(0, str(_candidate))
        break

from color_object_model import LargestColorObjectModel
from object_coordinates import get_object_coordinates, get_target_bounding_box_coordinates
from distance_on_line_crossing import line_y_from_target, crossed_line

# Safe/expected ranges for each commanded angle, used to clip NN predictions.
ANGLE_X_MIN, ANGLE_X_MAX = -45, 45       # degrees, posX
BACKSWING_MIN, BACKSWING_MAX = -60, -30  # degrees, posY wind-up
RELEASE_MIN, RELEASE_MAX = 35, 60        # degrees, posY release

REST_X, REST_Y = 0, -30
RELOAD_WAIT_TIME = 10.0  # seconds to pause at rest before prompting for the next throw

settle_time = 0.5
MODEL_PATH = "model.joblib"
SPEED_1 = 10   # slow speed for the backswing wind-up
SPEED_2 = 100  # fast speed for the release

CATCH_TIMEOUT = 3.0  # seconds to watch the camera for a line crossing before giving up

# LAB thresholds for the ball ("object") and the target line ("target").
# Defaults copied from biggest_white_object_tracker/track_camera.py -- recalibrate
# with the existing colorpicker for the actual ball/line colors in use.
OBJECT_LOW = [61, 35, 0]
OBJECT_HIGH = [253, 162, 121]
TARGET_LOW = [0, 76, 145]
TARGET_HIGH = [179, 140, 171]
MIN_AREA = 100.0


THROW_PLAN = [
    # (angle_x, y_backswing, y_release)
]

_cam = None
_module = None
_object_model = LargestColorObjectModel(OBJECT_LOW, OBJECT_HIGH, MIN_AREA, label_id=0)
_target_model = LargestColorObjectModel(TARGET_LOW, TARGET_HIGH, MIN_AREA, label_id=1)


def initialize_camera():
    global _cam
    _cam = ct.prepare_camera()
    while True:
        frame = ct.capture_image(_cam)
        if get_target_bounding_box_coordinates(frame, _target_model) is not None:
            break

def initialize_robot(module=None):
    global _module
    api.setup(blocking=True)
    moduleids = api.discoverModules()
    if not moduleids:
        raise RuntimeError("No Fable modules found. Check that the module is powered on and connected to the dongle.")

    _module = module if module is not None else moduleids[0]
    api.setSpeed(SPEED_1, SPEED_1, _module)
    api.setPos(0, 0, _module)
    api.sleep(0.5)

def move_joint(x_deg: float, y_deg: float = 0.0) -> None:
    api.setPos(x_deg, y_deg, _module)

def go_to_rest():
    api.setSpeed(SPEED_1, SPEED_1, _module)
    move_joint(REST_X, REST_Y)

def wait_for_next_throw_command():
    time.sleep(RELOAD_WAIT_TIME)
    return input("Click enter to throw: q to quit").strip().lower()

def wait_for_landing_x():

    previous_side = None
    was_on_line = False
    deadline = time.time() + CATCH_TIMEOUT

    while time.time() < deadline:
        frame = ct.capture_image(_cam)
        target_coordinates = get_target_bounding_box_coordinates(frame, _target_model)
        object_coordinates = get_object_coordinates(frame, _object_model)

        if target_coordinates is None or object_coordinates is None:
            previous_side = None
            was_on_line = False
            continue

        line_y = line_y_from_target(target_coordinates)
        crossed, previous_side, was_on_line = crossed_line(
            object_coordinates.box, line_y, previous_side, was_on_line
        )
        if crossed:
            return object_coordinates.center[0]

    return None

def throw_and_measure(angle_x, y_backswing, y_release):
    api.setSpeed(SPEED_1, SPEED_1, _module)
    move_joint(angle_x, y_backswing)
    time.sleep(settle_time)

    api.setSpeed(SPEED_2, SPEED_2, _module)
    move_joint(angle_x, y_release)

    x = wait_for_landing_x()
    go_to_rest()
    return x

def collect_data():
    assert THROW_PLAN, "THROW_PLAN empty"

    go_to_rest()
    xs, x_cmd, backswing_cmd, release_cmd = [], [], [], []
    for angle_x, y_backswing, y_release in THROW_PLAN:
        command = wait_for_next_throw_command()
        if command == "q":
            break

        x = throw_and_measure(angle_x, y_backswing, y_release)
        if x is not None and np.isfinite(x):
            xs.append(x)
            x_cmd.append(angle_x)
            backswing_cmd.append(y_backswing)
            release_cmd.append(y_release)

    return np.array(xs), np.array(x_cmd), np.array(backswing_cmd), np.array(release_cmd)

def make_scaler(v):
    lo, hi = float(np.min(v)), float(np.max(v))

    if np.isclose(lo, hi):
        raise ValueError("Cannot normalize data: min and max are equal.")

    return{"lo": lo, "hi": hi}

def norm(v, s): return (v - s["lo"]) / (s["hi"] - s["lo"])
def denorm(v, s): return v * (s["hi"] - s["lo"]) + s["lo"]

def train_model(x_obs, x_cmd, backswing_cmd, release_cmd):
    x_scaler = make_scaler(x_obs)
    angle_x_scaler = make_scaler(x_cmd)
    backswing_scaler = make_scaler(backswing_cmd)
    release_scaler = make_scaler(release_cmd)

    X = norm(x_obs, x_scaler).reshape(-1, 1)
    y = np.column_stack([
        norm(x_cmd, angle_x_scaler),
        norm(backswing_cmd, backswing_scaler),
        norm(release_cmd, release_scaler),
    ])

    Xtr, Xval, y_tr, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    net = MLPRegressor(
                        hidden_layer_sizes=(8, 8),
                        activation='tanh',
                        solver='adam',
                        max_iter=1000,
                        random_state=42)

    net.fit(Xtr, y_tr)
    val_mse = np.mean((net.predict(Xval) - y_val) ** 2)
    print(f"Validation MSE: {val_mse:.6f}")
    return {
        "net": net,
        "x_scaler": x_scaler,
        "angle_x_scaler": angle_x_scaler,
        "backswing_scaler": backswing_scaler,
        "release_scaler": release_scaler,
    }

def validate(model, x_obs, x_cmd, backswing_cmd, release_cmd):
    x_scaler = model["x_scaler"]
    outputs = [
        ("angle_x", model["angle_x_scaler"], x_cmd),
        ("y_backswing", model["backswing_scaler"], backswing_cmd),
        ("y_release", model["release_scaler"], release_cmd),
    ]

    grid = np.linspace(x_obs.min(), x_obs.max(), 200)
    pred = model["net"].predict(norm(grid, x_scaler).reshape(-1, 1))

    monotonic = {}
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    for i, (label, scaler, measured) in enumerate(outputs):
        pred_i = denorm(pred[:, i], scaler)
        d = np.diff(pred_i)
        tol = 1e-4
        monotonic[label] = bool(np.all(d >= -tol) or np.all(d <= tol))

        axes[i].scatter(x_obs, measured, s=5, label="Measured")
        axes[i].plot(grid, pred_i, label="MLP")
        axes[i].set_xlabel("x [pixels]")
        axes[i].set_ylabel(label)
        axes[i].legend()

    print("Monotonic:", monotonic)
    fig.tight_layout()
    plt.show()

    return monotonic

def predict_throw(x_target, model):
    x_scaler = model["x_scaler"]

    x_target = np.clip(x_target, x_scaler["lo"], x_scaler["hi"])
    xn = norm(np.array([[x_target]]), x_scaler)

    pred = model["net"].predict(xn)[0]
    angle_x = denorm(pred[0], model["angle_x_scaler"])
    y_backswing = denorm(pred[1], model["backswing_scaler"])
    y_release = denorm(pred[2], model["release_scaler"])

    angle_x = float(np.clip(angle_x, ANGLE_X_MIN, ANGLE_X_MAX))
    y_backswing = float(np.clip(y_backswing, BACKSWING_MIN, BACKSWING_MAX))
    y_release = float(np.clip(y_release, RELEASE_MIN, RELEASE_MAX))
    return angle_x, y_backswing, y_release

if __name__ == "__main__":
    initialize_camera()
    initialize_robot()

    x_obs, x_cmd, backswing_cmd, release_cmd = collect_data()
    np.savez("data_raw.npz", x=x_obs, angle_x=x_cmd, y_backswing=backswing_cmd, y_release=release_cmd)

    model = train_model(x_obs, x_cmd, backswing_cmd, release_cmd)
    validate(model, x_obs, x_cmd, backswing_cmd, release_cmd)

    joblib.dump(model, MODEL_PATH)     # creates the model
    print(f"Model saved to {MODEL_PATH}")