import csv
import select
import sys
import time
from pathlib import Path

import cv2
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
from distance_on_line_crossing import (
    line_y_from_target,
    crossed_line,
    draw_annotation,
    draw_line,
)

# Safe/expected ranges for each commanded angle, used to clip NN predictions.
ANGLE_X_MIN, ANGLE_X_MAX = -45, 45       # degrees, posX
BACKSWING_MIN, BACKSWING_MAX = -60, -30  # degrees, posY wind-up
RELEASE_MIN, RELEASE_MAX = 35, 60        # degrees, posY release

REST_X, REST_Y = 0, -30
RELOAD_WAIT_TIME = 10.0  # seconds to pause at rest before prompting for the next throw

settle_time = 1.5
MODEL_PATH = "model.joblib"
SPEED_1 = 10   # slow speed for the backswing wind-up
SPEED_2 = 100  # fast speed for the release

CATCH_TIMEOUT = 3.0  # seconds to watch the camera for a line crossing before giving up
MIN_FLIGHT_TIME = 0.3  # seconds after the release command during which crossings are ignored
                        # (guards against the launcher arm/cup itself sweeping past the target
                        # row before the ball is actually released -- tune this to how long the
                        # backswing->release swing actually takes on your rig)

SHOW_PREVIEW = True  # live cv2 window of what the camera sees; set False for headless runs
PREVIEW_WINDOW = "camera_to_angle: live view"

# LAB thresholds for the ball ("object") and the target line ("target").
# Defaults copied from biggest_white_object_tracker/track_camera.py -- recalibrate
# with the existing colorpicker for the actual ball/line colors in use.
OBJECT_LOW = [ 69, 121,  93]
OBJECT_HIGH = [ 98, 145, 118]
TARGET_LOW = [ 15, 145, 136]
TARGET_HIGH = [255, 255, 255]
MIN_AREA = 100.0


TRAINING_CSV = Path(__file__).resolve().parent / "notebooks" / "training_data.csv"

# Column names in the training CSV -- change these if the CSV schema changes.
COL_PX = "px"
COL_ANGLE_X = "x"
COL_BACKSWING = "y1"
COL_RELEASE = "y2"

def load_training_data(csv_path):
    """Loads (x_target, angle_x, y_backswing, y_release) columns from the training CSV."""
    with open(csv_path, newline="") as f:
        dialect = csv.Sniffer().sniff(f.readline(), delimiters="\t,")
        f.seek(0)
        reader = csv.DictReader(f, dialect=dialect)
        rows = [
            (float(row[COL_PX]), float(row[COL_ANGLE_X]), float(row[COL_BACKSWING]), float(row[COL_RELEASE]))
            for row in reader
        ]
    x_obs, x_cmd, backswing_cmd, release_cmd = (np.array(col) for col in zip(*rows))
    return x_obs, x_cmd, backswing_cmd, release_cmd

_cam = None
_module = None
_object_model = LargestColorObjectModel(OBJECT_LOW, OBJECT_HIGH, MIN_AREA, label_id=0)
_target_model = LargestColorObjectModel(TARGET_LOW, TARGET_HIGH, MIN_AREA, label_id=1)


def show_preview(frame, target_coordinates=None, object_coordinates=None):
    "Draw the current detections over the frame and show it in a live cv2 window."
    if not SHOW_PREVIEW:
        return

    preview = frame
    if target_coordinates is not None:
        preview = draw_annotation(
            preview,
            target_coordinates.box,
            target_coordinates.normalized_box,
            target_coordinates.area,
            target_coordinates.label_id,
            label="target",
            box_color=(0, 255, 255),
        )
        draw_line(preview, target_coordinates)
    if object_coordinates is not None:
        preview = draw_annotation(
            preview,
            object_coordinates.box,
            object_coordinates.normalized_box,
            object_coordinates.area,
            object_coordinates.label_id,
            label="object",
            box_color=(255, 0, 0),
        )

    cv2.imshow(PREVIEW_WINDOW, preview)
    cv2.waitKey(1)  # lets the window actually repaint; does not block/pause the script

def close_preview():
    if SHOW_PREVIEW:
        cv2.destroyAllWindows()
        for _ in range(4):  # flush pending GUI events so the window actually closes
            cv2.waitKey(1)

def initialize_camera():
    global _cam
    _cam = ct.prepare_camera()  # laptop webcam (cv2.VideoCapture(0)); RealSenseColorCapture
                                 # from distance_on_line_crossing is the alternative if switching back
    while True:
        frame = ct.capture_image(_cam)
        target_coordinates = get_target_bounding_box_coordinates(frame, _target_model)
        show_preview(frame, target_coordinates=target_coordinates)
        if target_coordinates is not None:
            print(f"Target detected: box={target_coordinates.box} center={target_coordinates.center}")
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

def _idle_preview(duration):
    "Keep showing the live feed (and pumping the cv2 window) instead of a blind time.sleep."
    if not SHOW_PREVIEW:
        time.sleep(duration)
        return
    deadline = time.time() + duration
    while time.time() < deadline:
        frame = ct.capture_image(_cam)
        show_preview(frame)

def _input_with_preview(prompt):
    "input() that keeps pumping the preview window while it waits on stdin, so cv2 doesn't hang."
    print(prompt, end="", flush=True)
    if not SHOW_PREVIEW:
        return input()
    while True:
        frame = ct.capture_image(_cam)
        show_preview(frame)
        ready, _, _ = select.select([sys.stdin], [], [], 0)
        if ready:
            return sys.stdin.readline().rstrip("\n")

def wait_for_next_throw_command():
    _idle_preview(RELOAD_WAIT_TIME)
    return _input_with_preview("Click enter to throw: q to quit, f to finish and report").strip().lower()

def get_target_x():
    """Reads one frame and returns the target's current x (pixels), or raises if not visible."""
    frame = ct.capture_image(_cam)
    target_coordinates = get_target_bounding_box_coordinates(frame, _target_model)
    if target_coordinates is None:
        raise RuntimeError("Target not visible in the camera frame.")
    return target_coordinates.center[0]

def wait_for_target_x():
    """Blocks (retrying) until the target is visible, then returns its x (pixels)."""
    while True:
        try:
            return get_target_x()
        except RuntimeError:
            continue

def wait_for_landing_x():

    previous_side = None
    was_on_line = False
    start = time.time()
    deadline = start + CATCH_TIMEOUT

    while time.time() < deadline:
        frame = ct.capture_image(_cam)
        target_coordinates = get_target_bounding_box_coordinates(frame, _target_model)
        object_coordinates = get_object_coordinates(frame, _object_model)
        show_preview(frame, target_coordinates=target_coordinates, object_coordinates=object_coordinates)

        if target_coordinates is None or object_coordinates is None:
            previous_side = None
            was_on_line = False
            continue

        line_y = line_y_from_target(target_coordinates)
        crossed, previous_side, was_on_line = crossed_line(
            object_coordinates.box, line_y, previous_side, was_on_line
        )
        # Ignore crossings in the first MIN_FLIGHT_TIME seconds: the ball physically cannot
        # have reached the target yet, so this is almost always the launcher arm/cup itself
        # sweeping past the target's row while it's still mid-swing, not a real throw.
        if crossed and (time.time() - start) >= MIN_FLIGHT_TIME:
            print(f"Ball crossed target line: box={object_coordinates.box} center={object_coordinates.center}")
            return object_coordinates.center[0]

    return None

def throw_and_measure(angle_x, y_backswing, y_release, on_release=None):
    print(f"Throw: angle_x={angle_x} y_backswing={y_backswing} y_release={y_release}")
    api.setSpeed(SPEED_1, SPEED_1, _module)
    go_to_rest()
    time.sleep(settle_time)
    move_joint(angle_x, y_backswing)
    time.sleep(settle_time)

    api.setSpeed(SPEED_2, SPEED_2, _module)
    move_joint(angle_x, y_release)
    if on_release is not None:
        on_release()  # let the caller know the release command was just sent
                       # (e.g. to start trusting mic input for impact detection)
    time.sleep(settle_time)
    go_to_rest()

    x = wait_for_landing_x()

    return x

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
    # Training only needs the CSV -- no camera/robot required.
    x_obs, x_cmd, backswing_cmd, release_cmd = load_training_data(TRAINING_CSV)

    model = train_model(x_obs, x_cmd, backswing_cmd, release_cmd)
    validate(model, x_obs, x_cmd, backswing_cmd, release_cmd)

    joblib.dump(model, MODEL_PATH)     # creates the model
    print(f"Model saved to {MODEL_PATH}")

    # Manual testing (run interactively, e.g. in a console/notebook):
    #   model = joblib.load(MODEL_PATH)
    #   initialize_camera()
    #   initialize_robot()
    #   angle_x, y_backswing, y_release = predict_throw(x_target, model)
    #   landing_x = throw_and_measure(angle_x, y_backswing, y_release)