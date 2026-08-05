import numpy as np
import matplotlib.pyplot as plt


Rm = 10*1e6 # Mega Ohm
Cm = 1*1e-9 # Nano Farad
u_thresh = -50*1e-3 # milli Volt
u_rest = -65*1e-3 # milli Volt

# Point 1.1
def LIF(um_0, I, T):
    
    delta_t = 1e-5 
    um_t = np.zeros((int(T//delta_t)))
    um_t[0] = um_0
    t = np.arange(len(um_t))*delta_t

    dum_dt = lambda um_t: (u_rest - um_t + Rm*I)/(Rm*Cm)
    # TODO Calculate the um_t from T = 0 until T in steps of delta-t
    for i in range(1, len(um_t)):
        um_t[i] = um_t[i-1] + dum_dt(um_t[i-1])*delta_t
        if um_t[i] > u_thresh:
            um_t[i] = u_rest
    return um_t, t


# Point 1.2
Ts = 0.1 # 100 ms
# TODO: Calculate the membrane potential using the LIF function from Point 1.1
membrane_potential, t = LIF(u_rest, 1e-9, Ts)

plt.figure(figsize=(7,5))
plt.plot(t, membrane_potential)
plt.xlabel('Time [s]')
plt.ylabel('Membrane potential [V]')
plt.show()

# Minimum current to spike: steady-state u_m = u_rest + Rm*I must exceed u_thresh
I_min = (u_thresh - u_rest)/Rm
print('Minimum current to produce a spike: {:.3f} nA'.format(I_min*1e9))


# Point 1.3
# TODO: Define a function to calculate the interspike intervals
def calculate_isi(membrane_potential, t):
    drops = np.where(np.diff(membrane_potential) < -1e-3)[0] + 1
    spike_times = t[drops]
    return np.diff(spike_times)

# TODO: Define a function to calculate the spiking frequency of a whole experiment
def spiking_frequency(membrane_potential, t):
    isi = calculate_isi(membrane_potential, t)
    if len(isi) == 0:
        return 0.0
    return 1/np.mean(isi)

membrane_potential2, t2 = LIF(u_rest, 2e-9, Ts)
plt.figure(figsize=(7,5))
plt.plot(t2, membrane_potential2)
plt.show()
print('ISI:', calculate_isi(membrane_potential2, t2))
print('Spiking frequency: {:.2f} Hz'.format(spiking_frequency(membrane_potential2, t2)))


# Point 1.4
plt.figure(figsize=(7,5))
spikes = []
# TODO write the code to accumulate the spikes
for current in np.arange(0,5.5e-9, 0.5e-9): #Solution here
    membrane_potential_i, t_i = LIF(u_rest, current, Ts)
    spikes.append(spiking_frequency(membrane_potential_i, t_i))

plt.plot(list(np.arange(0,5.5e-9, 0.5e-9)), spikes)
plt.xlabel('Constant current')
plt.ylabel('Spiking frequency')
plt.show()