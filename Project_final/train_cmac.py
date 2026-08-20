"""
Stand-alone CMAC warm-up.

Trains the CMAC on a synthetic replay of the target's known movement -- the same
7 measured pixel_x positions used everywhere else in the project (see
notebooks/get_angles_for_nn.ipynb), stepped through back and forth at 50 BPM --
instead of a live camera warm-up. This is the same scheme validated in
notebooks/test_cmac_pingpong.ipynb (83% next-position accuracy after ~300s of
this synthetic training; SYNTHETIC_TRAINING_DURATION below trains for longer),
just run here so main.py can load pretrained weights via --no-warmup instead
of retraining from scratch every run.

Runs in simulated time (no real sleeping), so it doesn't need the camera or the
robot at all -- just run this to pre-train the CMAC.
"""
import time

from cmac import CMAC3, DEFAULT_WEIGHTS_PATH, padded_input_range
from config import N_CENTERS, TIME_OF_FLIGHT, POLL_INTERVAL
from reporting import plot_prediction, report_learning

# Deliberately NOT config.WARMUP_DURATION -- that constant is also used as a real
# wall-clock duration by main.py's live camera warm-up (see config.py), whereas this
# runs in simulated time and is essentially free, so it's fine for it to be much
# longer. Bump this if the CMAC still isn't converged; it doesn't cost real time.
SYNTHETIC_TRAINING_DURATION = 1000.0  # seconds of simulated target movement

# Same 7 measured pixel_x positions as notebooks/get_angles_for_nn.ipynb /
# notebooks/test_cmac_pingpong.ipynb, left -> right across the camera frame.
PIXEL_X_VALS = [462, 406, 344, 276, 216, 150, 90]
PINGPONG_PERIOD = 2 * (len(PIXEL_X_VALS) - 1)  # beats to complete a full back-and-forth cycle


def pingpong_index(beat):
    """Maps an integer beat number to an index into PIXEL_X_VALS, bouncing back
    and forth across the 7 positions: 0,1,2,3,4,5,6,5,4,3,2,1,0,1,2,..."""
    phase = beat % PINGPONG_PERIOD
    return phase if phase < len(PIXEL_X_VALS) else PINGPONG_PERIOD - phase


def target_x(t, beat_dt):
    """Synthetic target x position (pixels) at simulated time t [s]. Zero-order
    hold: the target sits at one of the 7 measured positions for beat_dt seconds
    (one "movement" -- beat_dt = 60/BPM), then jumps to the next one, going back
    and forth."""
    # NOTE: int(t // beat_dt) looks equivalent but isn't -- for beat_dt=1.2 (a value
    # not exactly representable in binary float), t // beat_dt can be off by one
    # due to float rounding (e.g. 3*1.2 // 1.2 == 2.0, not 3.0). True division then
    # truncating avoids that -- see notebooks/test_cmac_pingpong.ipynb, which uses
    # the same int(t / beat_dt) form for this reason.
    beat = int(t / beat_dt)
    return float(PIXEL_X_VALS[pingpong_index(beat)])


def train_on_synthetic_movement(cmac, time_of_flight, duration, poll_interval, start_time=None):
    """
    Trains `cmac` on the synthetic 7-position back-and-forth movement instead of
    live camera samples -- same online scheme cmac_warmup.warmup() uses for the
    live case (sliding window of 3 consecutive movements poll_interval apart,
    true value time_of_flight seconds after the 3rd), but stepping through
    simulated time instead of real time, so `duration` seconds of synthetic
    movement train in a couple seconds of wall-clock time.

    See notebooks/test_cmac_pingpong.ipynb for the validation of this scheme.

    Returns (window, times, y_true, y_pred), same shape as cmac_warmup.warmup(),
    so this drops into main() below the same way.
    """
    if start_time is None:
        start_time = time.time()

    n_beats = round(duration / poll_interval)
    window = [target_x(0, poll_interval), target_x(poll_interval, poll_interval), target_x(2 * poll_interval, poll_interval)]

    times, y_true, y_pred = [], [], []

    for beat in range(2, 2 + n_beats):
        t3 = beat * poll_interval
        x1, x2, x3 = window

        x_hat, B = cmac.predict(x1, x2, x3)
        x_true = target_x(t3 + time_of_flight, poll_interval)  # position time_of_flight seconds after x3

        error = x_true - x_hat
        cmac.update(B, error)

        times.append(time.time() - start_time)  # wall-clock timestamp for plotting, not simulated time
        y_true.append(x_true)
        y_pred.append(x_hat)

        # slide the window forward by one movement/beat
        window = [x2, x3, target_x(t3 + poll_interval, poll_interval)]

    return window, times, y_true, y_pred


def main():
    cmac = CMAC3(
        n_centers=N_CENTERS,
        input_range=padded_input_range(min(PIXEL_X_VALS), max(PIXEL_X_VALS), N_CENTERS),
        beta=0.05,  # matches the rate validated in notebooks/test_cmac_pingpong.ipynb --
                    # CMAC3's own default (0.1) overshoots/oscillates on this data.
    )

    start_time = time.time()
    _, times, y_true, y_pred = train_on_synthetic_movement(
        cmac, TIME_OF_FLIGHT, SYNTHETIC_TRAINING_DURATION, POLL_INTERVAL, start_time=start_time
    )
    report_learning(y_true, y_pred)

    # Record what horizon/spacing these weights were trained on, so main.py can warn
    # if config.py has since changed and these weights are now stale/mismatched.
    cmac.trained_time_of_flight = TIME_OF_FLIGHT
    cmac.trained_poll_interval = POLL_INTERVAL

    cmac.save(DEFAULT_WEIGHTS_PATH)
    print(f"Saved trained CMAC weights to {DEFAULT_WEIGHTS_PATH}")

    plot_prediction(times, y_true, y_pred)


if __name__ == "__main__":
    main()
