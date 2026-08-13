import numpy as np
import matplotlib.pyplot as plt

from robot import SingleLink
from cmac2 import CMAC

## Initialize simulation
Ts = 1e-2
T_end = 150 # in one trial
n_steps = int(T_end/Ts) # in one trial
n_trials = 10

plant = SingleLink(Ts)

## Logging variables
t_vec = np.array([Ts*i for i in range(n_steps*n_trials)])

theta_vec = np.zeros(n_steps*n_trials)
theta_ref_vec = np.zeros(n_steps*n_trials)

## Feedback controller variables
Kp = 3
Kv = 0.4

## TODO: Define parameters for periodic reference trajectory

A = np.pi / 4
T_period = 2.0
w_ref = 2 * np.pi / T_period

## TODO: CMAC initialization

n_rfs = 11
omega_max = A * w_ref

cmac = CMAC(
    n_rfs,
    [-A, -omega_max],
    [A, omega_max],
    beta=1e-2
)
## Simulation loop
for i in range(n_steps*n_trials):
    t = i*Ts
    ## TODO: Calculate the reference at this time step
    theta_ref = np.pi/4
    theta_ref = A * np.sin(w_ref * t)
    omega_ref = A * w_ref * np.cos(w_ref * t)
    # Measure
    theta = plant.theta
    omega = plant.omega

    # Feedback controller
    error = (theta_ref - theta)
    theta_error = theta_ref - theta
    omega_error = omega_ref - omega

    tau_m = Kp * theta_error + Kv * omega_error

    ## TODO: Implement the CMAC controller into the loop
    ## TODO: Implement the CMAC controller into the loop
    tau_cmac = cmac.predict([theta_ref, omega_ref])

    tau = tau_m + tau_cmac

    cmac.learn(tau_m)
    
    # Iterate simulation dynamics
    plant.step(tau)

    theta_vec[i] = plant.theta
    theta_ref_vec[i] = theta_ref



## Plotting
plt.plot(t_vec, theta_vec, label='theta')
plt.plot(t_vec, theta_ref_vec, '--', label='reference')
plt.legend()

## Plot trial error
error_vec = theta_ref_vec - theta_vec
l = int(T_period/Ts)
trial_error = np.zeros(n_trials)
for t in range(n_trials):
    trial_error[t] = np.sqrt( np.mean( error_vec[t*l:(t+1)*l]**2 ) )
plt.figure()
plt.plot(trial_error)

plt.show()