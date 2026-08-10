import numpy as np
import matplotlib.pyplot as plt

from adaptive_filter.cerebellum import AdaptiveFilterCerebellum
from robot import SingleLink

Ts = 1e-3 #sample time (s)
#n_inputs = # filter-bank input dimension
#n_outputs = # output dimension (one correction C)
#n_bases =  #number of basis filters Gi(s)
#beta = #learning rate scaled by Ts and #bases

# Adaptive Filter
#c = AdaptiveFilterCerebellum(Ts, n_inputs, n_outputs, n_bases, beta)

## TODO: Paste your experiment code from exercise 2.6
## TODO: Change the code to the recurrent architecture
# You can update the cerebellum with: C = c.step(u, error)

## TODO: Plot results