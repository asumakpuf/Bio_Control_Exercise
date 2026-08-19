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

theta_min, theta_max = -45, 45 #in degrees
n_steps = 200 #number of steps for theta
n_repeats = 2 #number of repeats for each theta value
settle_time = 0.5
MODEL_PATH   = "model.joblib"
SPEED_1 = 10 #joint speed, 1-100 percent
SPEED_2 = 100 #joint speed, 1-100 percent

BACKSWING_Y = -30
RELEASE_Y = 60
CATCH_TIMEOUT = 3.0  # seconds to watch the camera for a line crossing before giving up

OBJECT_LOW = [61, 35, 0]
OBJECT_HIGH = [253, 162, 121]
TARGET_LOW = [0, 76, 145]
TARGET_HIGH = [179, 140, 171]
MIN_AREA = 100.0

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
    api.setSpeed(SPEED, SPEED, _module)
    api.setPos(0, 0, _module)
    api.sleep(0.5)

def move_joint(x_deg: float, y_deg: float = 0.0) -> None:

    api.setPos(x_deg, y_deg, _module)

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

def throw_and_measure(theta_deg):

    move_joint(theta_deg, BACKSWING_Y)
    time.sleep(settle_time)
    move_joint(theta_deg, RELEASE_Y)
    return wait_for_landing_x()

def collect_data():

    angles = np.linspace(theta_min, theta_max, n_steps)
    xs, thetas = [], []
    for r in range(n_repeats):
        sweep = angles if r % 2 == 0 else angles[::-1]  # Alternate sweep direction
        for theta in sweep:
            x = throw_and_measure(theta)
            if x is not None and np.isfinite(x):
                xs.append(x)
                thetas.append(theta)
    return np.array(xs), np.array(thetas)

def make_scaler(v):
    lo, hi = float(np.min(v)), float(np.max(v))

    if np.isclose(lo, hi):
        raise ValueError("Cannot normalize data: min and max are equal.")

    return{"lo": lo, "hi": hi}

def norm(v, s): return (v - s["lo"]) / (s["hi"] - s["lo"])
def denorm(v, s): return v * (s["hi"] - s["lo"]) + s["lo"]

def train_model(x_obs, thetas_cmd):
    xs = make_scaler(x_obs)
    ts = make_scaler(thetas_cmd)
    X = norm(x_obs, xs).reshape(-1, 1)
    y = norm(thetas_cmd, ts)

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
    return {"net": net, "x_scaler": xs, "theta_scaler": ts}

def validate(model, x_obs, theta_cmd):
    xs = model["x_scaler"]
    ts = model["theta_scaler"]

    grid = np.linspace(x_obs.min(), x_obs.max(), 200)

    pred = denorm(
        model["net"].predict(
            norm(grid, xs).reshape(-1, 1)
        ),
        ts
    )

    d = np.diff(pred)

    tol = 1e-4

    monotonic = np.all(d >= -tol) or np.all(d <= tol)

    print("Monotonic:", monotonic)

    plt.scatter(x_obs, theta_cmd, s=5, label="Measured")
    plt.plot(grid, pred, label="MLP")
    plt.xlabel("x [pixels]")
    plt.ylabel("theta [degrees]")
    plt.legend()
    plt.show()

    return monotonic

def predict_theta(x_target, model):
    xs = model["x_scaler"]
    ts = model["theta_scaler"]

    x_target = np.clip(
        x_target,
        xs["lo"],
        xs["hi"]
    )

    xn = norm(
        np.array([[x_target]]),
        xs
    )

    theta = float(
        denorm(
            model["net"].predict(xn),
            ts
        )[0]
    )

    return float(np.clip(theta, theta_min, theta_max))

if __name__ == "__main__":
    initialize_camera()
    initialize_robot()

    x_obs, theta_cmd = collect_data()
    np.savez("data_raw.npz", x=x_obs, theta=theta_cmd) 
 
    model = train_model(x_obs, theta_cmd)
    validate(model, x_obs, theta_cmd)
 
    joblib.dump(model, MODEL_PATH)     # creates the model
    print(f"Model saved to {MODEL_PATH}")