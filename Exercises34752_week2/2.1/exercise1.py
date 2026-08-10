from turtle import delay

import numpy as np
import matplotlib.pyplot as plt

## Initialization
# Length of simulation (time steps)
simlen = 30
# Output
y = np.zeros((simlen))
# Target
target = 0.0

# Controller gain
#K = 1
#delay = 2

# Set first output
y[0] = 1

for delay in [0, 1, 2]: 
    for K in [0.5, 1.5]:
        y = np.zeros((simlen))
        y[0] = 1
        ## Simulation
        for t in range(simlen-1):
            # TODO include the time delay
            idx = t - delay
            y_delayed = y[idx] if idx >= 0 else y[0]
            # Compute output
            u = K * (target - y_delayed)
            y[t+1]=0.5*y[t] + 0.4*u # 1st order dynamics
        plt.plot(range(simlen), y, label=f'delay = {delay}, K = {K}')

plt.xlabel('time step')
plt.ylabel('y')
plt.legend()
plt.show()