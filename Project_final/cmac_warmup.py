"""
Runs a CMAC in prediction-only mode (no throwing) so it has learned weights
before the robot starts actually throwing at the moving target.
"""
import time
from collections import deque


def warmup(cmac, get_target_x, time_of_flight, duration=30.0, poll_interval=0.5, start_time=None):
    """
    Samples the target position every `poll_interval` seconds into a rolling
    buffer and turns every new sample into a training update once the buffer
    holds enough history -- instead of the old scheme of one full
    time_of_flight-second wait per update.

    x1, x2, x3 are always 3 *consecutive* samples in the buffer (poll_interval
    apart), and the true position used for the error is always exactly
    time_of_flight seconds after x3 -- that horizon is fixed by the physical
    ball flight time, it's not something this function is free to change.
    Only the sampling/update rate (poll_interval) is decoupled from it.

    Concretely: the buffer holds `2 + horizon_steps + 1` samples, where
    horizon_steps = time_of_flight / poll_interval. The 3 OLDEST samples are
    used as (x1, x2, x3) and the sample that just arrived (time_of_flight
    seconds after x3) is used as x_true -- so once the buffer is full, every
    single poll produces one weight update.

    Args:
        cmac: object with predict(x1, x2, x3) -> (x_hat, B) and update(B, error).
        get_target_x: zero-arg callable returning the target's current x (pixels).
        time_of_flight: seconds from x3 to the position being predicted --
            fixed by the physical ball flight time, tune on the robot.
        duration: seconds to keep predicting/updating before returning.
        poll_interval: seconds between buffered samples. Independent of
            time_of_flight -- this is the knob that trades off buffer-fill
            latency against how many updates/second you get.
        start_time: reference time.time() for the `times` list below.
            Defaults to the moment warmup() is called; pass the same
            start_time the live throwing loop uses so warm-up and live
            updates land on one continuous timeline for plotting.

    Returns:
        (window, times, y_true, y_pred):
          - window: the final 3-sample window (x1, x2, x3), poll_interval
            apart, so the caller can continue predicting from it.
          - times/y_true/y_pred: one entry per weight update made during
            warm-up (times relative to start_time), for learning-curve
            reporting/plotting.
    """
    if start_time is None:
        start_time = time.time()

    horizon_steps = round(time_of_flight / poll_interval)
    buffer = deque(maxlen=2 + horizon_steps + 1)

    fill_time = buffer.maxlen * poll_interval
    print(f"CMAC warm-up: predicting for {duration:.0f}s "
          f"(buffer fills in ~{fill_time:.1f}s, then one update every {poll_interval:.1f}s)...")

    times, y_true, y_pred = [], [], []

    deadline = time.time() + duration
    while time.time() < deadline:
        step_start = time.time()

        buffer.append(get_target_x())
        if len(buffer) == buffer.maxlen:
            x1, x2, x3 = buffer[0], buffer[1], buffer[2]
            x_true = buffer[-1]

            x_hat, B = cmac.predict(x1, x2, x3)
            error = x_true - x_hat
            cmac.update(B, error)

            times.append(time.time() - start_time)
            y_true.append(x_true)
            y_pred.append(x_hat)
            print(f"warm-up: predicted_x={x_hat:.1f} true_x={x_true:.1f} error={error:+.1f}")

        elapsed = time.time() - step_start
        time.sleep(max(0.0, poll_interval - elapsed))

    print(f"CMAC warm-up done ({len(times)} updates).")

    # Most recent 3 buffered samples, poll_interval apart -- NOT time_of_flight
    # apart. Whoever consumes this window and predicts with it must also wait
    # time_of_flight seconds for the "true" value, to stay consistent with
    # what the model was just trained on.
    return list(buffer)[-3:], times, y_true, y_pred
