"""
Runs a CMAC in prediction-only mode (no throwing) so it has learned weights
before the robot starts actually throwing at the moving target.
"""
import time


def warmup(cmac, get_target_x, time_of_flight, duration=30.0, start_time=None):
    """
    Seeds a 3-sample delay line from the live target position, then repeats:
    predict x(t+time_of_flight), wait that long, read the true position,
    compute the error and update the CMAC -- exactly like the throwing loop
    will, but the ball is never thrown.

    Args:
        cmac: object with predict(x1, x2, x3) -> (x_hat, B) and update(B, error).
        get_target_x: zero-arg callable returning the target's current x (pixels).
        time_of_flight: seconds between delay-line samples.
        duration: seconds to keep predicting before returning.
        start_time: time.time() reference for the returned `times`, so callers
            can keep a single continuous timeline across warm-up and later
            phases. Defaults to the moment warm-up starts.

    Returns:
        window: final 3-sample window, so the caller can continue from it.
        times, y_true, y_pred: per-prediction history (seconds since
            start_time, true target x, predicted target x), for plotting or
            checking that the CMAC's error is trending down.
    """
    print(f"CMAC warm-up: predicting for {duration:.0f}s without throwing...")

    if start_time is None:
        start_time = time.time()

    window = []
    for _ in range(3):
        window.append(get_target_x())
        time.sleep(time_of_flight)

    times, y_true, y_pred = [], [], []

    deadline = time.time() + duration
    while time.time() < deadline:
        x1, x2, x3 = window
        x_hat, B = cmac.predict(x1, x2, x3)

        time.sleep(time_of_flight)
        x_true = get_target_x()

        error = x_true - x_hat
        cmac.update(B, error)
        print(f"warm-up: predicted_x={x_hat:.1f} true_x={x_true:.1f} error={error:+.1f}")

        times.append(time.time() - start_time)
        y_true.append(x_true)
        y_pred.append(x_hat)

        window = [x2, x3, x_true]

    print("CMAC warm-up done.")
    return window, times, y_true, y_pred
