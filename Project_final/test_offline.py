"""
Offline test harness for camera_to_angle.py.

Runs the whole pipeline (collect_data -> train_model -> validate -> predict_theta)
against a simulated joint->pixel mapping instead of the real Fable + camera,
so it can be tested without any hardware connected.
"""
import numpy as np
import camera_to_angle as cta

rng = np.random.default_rng(0)

# --- Fake camera + robot -----------------------------------------------
X_CENTER = 320.0
PIXELS_PER_DEG = 4.0
NOISE_STD = 2.0

_true_theta = 0.0

def fake_move_joint(theta_deg):
    global _true_theta
    _true_theta = theta_deg

def fake_read_target_x():
    x = X_CENTER + PIXELS_PER_DEG * _true_theta + 0.01 * _true_theta**3
    return x + rng.normal(0, NOISE_STD)

def x_of_theta(theta_deg):
    """Noiseless version of fake_read_target_x, for checking predictions."""
    return X_CENTER + PIXELS_PER_DEG * theta_deg + 0.01 * theta_deg**3

# --- Patch the hardware-facing functions --------------------------------
cta.move_joint = fake_move_joint
cta.read_target_x = fake_read_target_x
cta.settle_time = 0.0   # skip real delays
cta.n_steps = 60         # fewer points -> faster test run
cta.n_repeats = 2

# --- Run the real pipeline, unmodified ----------------------------------
x_obs, theta_cmd = cta.collect_data()
print(f"Collected {len(x_obs)} points")

model = cta.train_model(x_obs, theta_cmd)
monotonic = cta.validate(model, x_obs)
print("Monotonic:", monotonic)

print("\ntrue theta -> predicted theta")
for test_theta in [-40, -20, 0, 20, 40]:
    x_test = x_of_theta(test_theta)
    pred = cta.predict_theta(x_test, model)
    print(f"{test_theta:8.1f}  ->  {pred:8.2f}")
