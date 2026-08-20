"""
Simple discrete PD controller used as a persistent trim on top of the
pre-trained NN's angle_x output. Not tied to any fixed dt -- the "derivative"
term is per-update (per-throw), not per-second.
"""


class PDController:
    def __init__(self, kp, kd):
        self.kp = kp
        self.kd = kd
        self.prev_error = None
        self.correction = 0.0

    def update(self, error):
        """
        Feeds a new measured error (landing_x - x_target -- NOT x_target - landing_x;
        on this rig d(landing_x)/d(angle_x) < 0, see calibrate_pd_sign.py and the note
        in throw_at_target.py's throw_once) and updates the correction to use on the
        next throw. Returns the new correction.
        """
        derivative = 0.0 if self.prev_error is None else (error - self.prev_error)
        self.prev_error = error
        self.correction = self.kp * error + self.kd * derivative
        return self.correction
