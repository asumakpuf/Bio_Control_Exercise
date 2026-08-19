"""
Runs a CMAC in prediction-only mode (no throwing) so it has learned weights
before the robot starts actually throwing at the moving target.
"""
import time


def warmup(cmac, get_target_x, time_of_flight, duration=30.0):
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

    Returns:
        The final 3-sample window, so the caller can continue from it.
    """
    print(f"CMAC warm-up: predicting for {duration:.0f}s without throwing...")

    window = []
    for _ in range(3):
        window.append(get_target_x())
        time.sleep(time_of_flight)

    deadline = time.time() + duration
    while time.time() < deadline:
        x1, x2, x3 = window
        x_hat, B = cmac.predict(x1, x2, x3)

        time.sleep(time_of_flight)
        x_true = get_target_x()

        error = x_true - x_hat
        cmac.update(B, error)
        print(f"warm-up: predicted_x={x_hat:.1f} true_x={x_true:.1f} error={error:+.1f}")

        window = [x2, x3, x_true]

    print("CMAC warm-up done.")
    return window
