import time
import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import train_test_split
import joblib
import matplotlib.pyplot as plt

import camera_tools as ct
from FableAPI.fable_init import api
theta_min, theta_max = -45, 45 #in degrees
n_steps = 200 #number of steps for theta
n_repeats = 2 #number of repeats for each theta value
settle_time = 0.5
MODEL_PATH   = "model.joblib"
SPEED = 50 #joint speed, 1-100 percent

_cam = None
_module = None


def initialize_camera():
    """Opens the camera and waits until the target is visible."""
    global _cam
    _cam = ct.prepare_camera()
    while True:
        frame = ct.capture_image(_cam)
        x, _ = ct.locate(frame)
        if x is not None:
            break

def initialize_robot(module=None):
    """Connects to the dongle and selects the Fable module to control."""
    global _module
    api.setup(blocking=True)
    moduleids = api.discoverModules()
    if not moduleids:
        raise RuntimeError("No Fable modules found. Check that the module is powered on and connected to the dongle.")

    _module = module if module is not None else moduleids[0]
    api.setSpeed(SPEED, SPEED, _module)
    api.setPos(0, 0, _module)
    api.sleep(0.5)

def move_joint(theta_deg:float)-> None:
    """
    Commands the Fable joint to move a specified angle in degrees.
    """
    api.setPos(theta_deg, 0, _module)

def read_target_x()-> float:
    """
    Reads the current x position of the target from the camera.
    """
    frame = ct.capture_image(_cam)
    x, _ = ct.locate(frame)
    return x

def collect_data():
    """
    Collects data by moving the joint through a range of angles and
    recording the corresponding x positions.
    Returns:
        xs: np.ndarray of x positions
        thetas: np.ndarray of corresponding angles
    """
    angles = np.linspace(theta_min, theta_max, n_steps)
    xs, thetas = [], []
    for r in range(n_repeats):
        sweep = angles if r % 2 == 0 else angles[::-1]  # Alternate sweep direction
        for theta in sweep:
            move_joint(theta)
            time.sleep(settle_time)
            x = read_target_x()
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