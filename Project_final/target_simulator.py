import numpy as np

class Simulator:
    def __init__(self, dt=0.5, model=None):
        
        self.dt = dt
        self.time = 0.0
        self.state = 0.0
        self.model = model

    def set_model(self, model):
        self.model = model

    def step(self):
        self.state = self.model.x(self.time)
        self.time += self.dt


class SimpleOscillation:
    def __init__(self, x_min, x_max, T):
        self.x0 = (x_max + x_min) / 2   # center of the range
        self.A = (x_max - x_min) / 2    # amplitude
        self.T = T                      # period
        self.w = 2 * np.pi / T
 
    def x(self, time):
        return self.x0 + self.A * np.sin(self.w * time)

class TwoHarmonicMotion:
    def __init__(self, x_min, x_max, T, phase2=np.pi/3, ratio2=0.4):
        self.x0 = (x_max + x_min) / 2
        self.A = (x_max - x_min) / 2
        self.T = T
        self.w = 2 * np.pi / T
        self.phase2 = phase2
        self.ratio2 = ratio2   # relative weight of the 2nd harmonic

        # precompute normalization constant over one full period
        t_ref = np.linspace(0, T, 2000)
        raw_ref = np.sin(self.w * t_ref) + self.ratio2 * np.sin(2 * self.w * t_ref + self.phase2)
        self.norm_const = np.max(np.abs(raw_ref))

    def x(self, time):
        raw = np.sin(self.w * time) + self.ratio2 * np.sin(2 * self.w * time + self.phase2)
        return self.x0 + self.A * raw / self.norm_const

    