import numpy as np
import matplotlib.pyplot as plt

from robot import SingleLink
from cmac2 import CMAC

Ts = 1e-2
Kp = 3
Kv = 0.4

## Exercise 3: baseline periodic reference trajectory parameters.
A = np.pi
T_period = 5.0
n_rfs = 11


def make_cmac(A, train_period, beta, use_joint_velocity=False):
    """Create a CMAC with input ranges covering the training trajectory."""
    omega_max = A * 2 * np.pi / train_period

    # Exercise 4: 2D CMAC inputs are desired position and desired velocity.
    xmin = [-A, -omega_max]
    xmax = [A, omega_max]

    if use_joint_velocity:
        # Exercise 7: optional 3D CMAC input adds measured joint velocity.
        xmin.append(-omega_max)
        xmax.append(omega_max)

    return CMAC(n_rfs, xmin, xmax, beta=beta)


def cmac_input(theta_ref, omega_ref, omega, use_joint_velocity):
    if use_joint_velocity:
        # Exercise 7: compare this 3D input against the standard 2D input.
        return [theta_ref, omega_ref, omega]
    return [theta_ref, omega_ref]


def run_experiment(
    A=np.pi,
    T_period=5.0,
    n_trials=50,
    beta=1e-2,
    cmac=None,
    learn=True,
    use_joint_velocity=False,
    cmac_train_period=None,
):
    """Run n trials where one trial is exactly one reference period."""
    plant = SingleLink(Ts)

    # Exercise 3: one trial is one complete reference period.
    n_steps = int(T_period / Ts)
    t_vec = np.array([Ts * i for i in range(n_steps * n_trials)])
    theta_vec = np.zeros(n_steps * n_trials)
    theta_ref_vec = np.zeros(n_steps * n_trials)

    w_ref = 2 * np.pi / T_period
    cmac_train_period = T_period if cmac_train_period is None else cmac_train_period
    if cmac is None:
        cmac = make_cmac(A, cmac_train_period, beta, use_joint_velocity)

    for i in range(n_steps * n_trials):
        t = i * Ts

        # Exercise 3: periodic reference theta_ref = A sin(2*pi*t/T).
        theta_ref = A * np.sin(w_ref * t)
        omega_ref = A * w_ref * np.cos(w_ref * t)

        theta = plant.theta
        omega = plant.omega

        # Exercise 4: feedback torque tau_m is the CMAC learning error signal.
        theta_error = theta_ref - theta
        omega_error = omega_ref - omega
        tau_m = Kp * theta_error + Kv * omega_error

        tau_cmac = cmac.predict(cmac_input(theta_ref, omega_ref, omega, use_joint_velocity))
        tau = tau_m + tau_cmac

        if learn:
            cmac.learn(tau_m)

        plant.step(tau)

        theta_vec[i] = plant.theta
        theta_ref_vec[i] = theta_ref

    # Exercise 5: mean squared position error per trial.
    error_vec = theta_ref_vec - theta_vec
    trial_error = np.zeros(n_trials)
    for trial in range(n_trials):
        start = trial * n_steps
        stop = (trial + 1) * n_steps
        trial_error[trial] = np.mean(error_vec[start:stop]**2)

    return cmac, t_vec, theta_vec, theta_ref_vec, trial_error


def first_flat_trial(trial_error, window=5, tolerance=0.01):
    """Estimate where trial MSE stops decreasing by more than tolerance."""
    if len(trial_error) < 2 * window:
        return None

    for trial in range(window, len(trial_error) - window):
        previous_mean = np.mean(trial_error[trial - window:trial])
        next_mean = np.mean(trial_error[trial:trial + window])
        if previous_mean > 0 and (previous_mean - next_mean) / previous_mean < tolerance:
            return trial

    return None


## Exercise 5: compare learning rates beta and plot trial MSE.
betas = [1e-2]
n_trials = 50

plt.figure()
for beta in betas:
    _, _, _, _, trial_error = run_experiment(
        A=A,
        T_period=T_period,
        n_trials=n_trials,
        beta=beta,
    )
    flat_trial = first_flat_trial(trial_error)
    label = f"beta={beta:g}"
    if flat_trial is not None:
        label += f""
    plt.plot(trial_error, label=label)

plt.title("Exercise 5: trial mean squared position error")
plt.xlabel("Trial")
plt.ylabel("MSE")
plt.legend()


## Exercise 4/5: show one baseline learned controller run.
trained_cmac, t_vec, theta_vec, theta_ref_vec, trial_error = run_experiment(
    A=A,
    T_period=T_period,
    n_trials=n_trials,
    beta=1e-2,
)

plt.figure()
plt.plot(t_vec, theta_vec, label="theta")
plt.plot(t_vec, theta_ref_vec, "--", label="reference")
plt.title("Exercise 4: CMAC assisted tracking during training")
plt.xlabel("Time [s]")
plt.ylabel("Position [rad]")
plt.legend()


## Exercise 6: test whether the trained CMAC generalizes to other frequencies.
frequency_tests = [
    ("higher frequency, T=2.5 s", 2.5),
    ("training frequency, T=5.0 s", 5.0),
    ("lower frequency, T=10.0 s", 10.0),
]

plt.figure()
for label, test_period in frequency_tests:
    _, t_test, theta_test, theta_ref_test, test_error = run_experiment(
        A=A,
        T_period=test_period,
        n_trials=1,
        beta=1e-2,
        cmac=trained_cmac,
        learn=False,
        cmac_train_period=T_period,
    )
    plt.plot(t_test, theta_ref_test - theta_test, label=f"{label}, MSE={test_error[0]:.3g}")

plt.title("Exercise 6: frequency generalization after convergence")
plt.xlabel("Time [s]")
plt.ylabel("Position error [rad]")
plt.legend()


## Exercise 7: optional comparison with actual joint velocity as a third CMAC input.
trained_cmac_3d, _, _, _, trial_error_3d = run_experiment(
    A=A,
    T_period=T_period,
    n_trials=n_trials,
    beta=1e-2,
    use_joint_velocity=True,
)

plt.figure()
plt.plot(trial_error, label="2D input: theta_ref, omega_ref")
plt.plot(trial_error_3d, label="3D input: theta_ref, omega_ref, omega")
plt.title("Exercise 7: adding measured joint velocity to CMAC input")
plt.xlabel("Trial")
plt.ylabel("MSE")
plt.legend()

plt.show()
