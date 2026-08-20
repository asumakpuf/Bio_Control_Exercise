"""
Loads the trained model, detects the target's current position with the
camera, and throws the ball at it.

Also times the throw with the microphone: since the camera-based landing
detection isn't reliable yet, we listen for the "thud" of the ball hitting
the table and use that instant as the landing time instead.
"""
import contextlib
import os
import threading
import time

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pyaudio

import camera_to_angle as cta
from pd_controller import PDController

RECENT_ERROR_WINDOW = 5  # throws averaged for the "recent" |error| printed after each throw

# Microphone-based impact detection. AUDIO_IMPACT_THRESHOLD is the RMS level
# (16-bit PCM) that counts as a "thud" -- there's no way to derive this from
# code, calibrate it with print_mic_levels() below and tap the table.
AUDIO_RATE = 44100
AUDIO_CHUNK = 1024
AUDIO_IMPACT_THRESHOLD = 150.0
IMPACT_TIMEOUT = 5.0  # seconds to listen for an impact before giving up

# PD trim applied on top of the NN's angle_x prediction, fed by the previous throw's
# (x_target - landing_x) error -- persistent across throws via a single PDController
# instance, not tied to any fixed dt (the "derivative" is per-throw). Tune on the robot.
PD_KP = 0.5  # proportional gain, degrees per pixel of landing error
PD_KD = 0.1  # derivative gain on the change in that error between throws


@contextlib.contextmanager
def _quiet_stderr():
    """
    Silences the ALSA/JACK "unable to open slave" / "jack server is not
    running" spam that PortAudio prints straight to the raw stderr file
    descriptor when pyaudio.PyAudio() is constructed. Those come from the C
    libraries below PyAudio, so redirecting sys.stderr in Python wouldn't
    catch them -- fd 2 itself has to be pointed at /dev/null instead.
    """
    stderr_fd = 2
    with open(os.devnull, "w") as devnull:
        saved_fd = os.dup(stderr_fd)
        try:
            os.dup2(devnull.fileno(), stderr_fd)
            yield
        finally:
            os.dup2(saved_fd, stderr_fd)
            os.close(saved_fd)


def _chunk_rms(stream):
    data = stream.read(AUDIO_CHUNK, exception_on_overflow=False)
    samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
    return float(np.sqrt(np.mean(samples ** 2)))


def print_mic_levels(duration=10.0):
    """Prints live microphone RMS levels -- use this to pick AUDIO_IMPACT_THRESHOLD."""
    with _quiet_stderr():
        pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16, channels=1, rate=AUDIO_RATE, input=True, frames_per_buffer=AUDIO_CHUNK)
    try:
        deadline = time.time() + duration
        while time.time() < deadline:
            print(f"mic rms: {_chunk_rms(stream):.0f}")
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()


def detect_impact(release_event, timeout=IMPACT_TIMEOUT):
    """
    Listens to the default microphone and returns the time.time() timestamp
    of the first chunk (after `release_event` is set) whose RMS level
    crosses AUDIO_IMPACT_THRESHOLD. Returns None if nothing crosses it
    within `timeout` seconds of the release.

    The stream is opened and read from immediately, before `release_event`
    fires -- that keeps the mic "warmed up" so no audio is missed right
    after release -- but chunks are only checked against the threshold and
    the timeout once the release has actually happened. This is what keeps
    the backswing/wind-up motor noise from being mistaken for the impact.
    """
    with _quiet_stderr():
        pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16, channels=1, rate=AUDIO_RATE, input=True, frames_per_buffer=AUDIO_CHUNK)
    try:
        deadline = None
        while True:
            rms = _chunk_rms(stream)
            if not release_event.is_set():
                continue
            if deadline is None:
                deadline = time.time() + timeout
            if rms > AUDIO_IMPACT_THRESHOLD:
                return time.time()
            if time.time() >= deadline:
                return None
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()


def throw_once(model, pd):
    """
    Detects the target, throws at it (with the PD controller's current correction
    trimmed onto angle_x), and prints timing/landing info for one throw. Feeds the
    resulting (landing_x - x_target) error back into `pd` for the next call.

    Returns a dict with x_target, angle_x (as commanded, i.e. NN + PD trim),
    pd_correction_used (the trim applied to THIS throw), landing_x and error
    (both None if no crossing was detected) -- for the caller to accumulate
    feedback-loop metrics across throws.
    """
    t_target_detected = time.time()
    x_target = cta.get_target_x()
    print(f"Target detected at x={x_target:.1f}")

    angle_x, y_backswing, y_release = cta.predict_throw(x_target, model)
    correction_used = pd.correction
    angle_x = float(np.clip(angle_x + correction_used, cta.ANGLE_X_MIN, cta.ANGLE_X_MAX))
    print(f"Predicted throw: angle_x={angle_x:.1f} (PD correction={correction_used:+.2f}) "
          f"y_backswing={y_backswing:.1f} y_release={y_release:.1f}")

    release_event = threading.Event()
    release_time = {}
    def mark_release():
        release_time["t"] = time.time()
        release_event.set()

    impact_result = {}
    listener = threading.Thread(target=lambda: impact_result.update(t=detect_impact(release_event)))
    listener.start()

    # throw_and_measure goes to the rest/base position before the backswing and again
    # right after release, so the arm only leaves the base position for the throw itself.
    # landing_fn=wait_for_landing_x_tracked: use the Kalman-based PurpleBallTracker for the
    # ball instead of the single-frame LargestColorObjectModel -- more robust mid-flight.
    landing_x = cta.throw_and_measure(
        angle_x, y_backswing, y_release,
        on_release=mark_release, landing_fn=cta.wait_for_landing_x_tracked,
    )

    listener.join()
    impact_time = impact_result.get("t")
    t_release = release_time.get("t")

    total_time = impact_time - t_target_detected if impact_time is not None else None
    flight_time = impact_time - t_release if impact_time is not None and t_release is not None else None
    if impact_time is not None:
        print(f"Impact detected at t={impact_time:.3f} "
              f"(flight time from release: {flight_time:.3f}s; total time from target detection: {total_time:.3f}s)")
    else:
        print(f"No impact detected within {IMPACT_TIMEOUT}s of release.")

    if landing_x is None:
        print("Could not detect where the ball landed (camera). PD correction left unchanged.")
        error = None
    else:
        # error = landing_x - x_target, NOT x_target - landing_x: calibration data
        # (notebooks/training_data_seven_pchip.csv) shows d(landing_x)/d(angle_x) < 0 on
        # this rig (angle_x=-40 -> px~462, angle_x=+40 -> px~90) -- see calibrate_pd_sign.py.
        error = landing_x - x_target
        pd.update(error)
        print(f"Ball landed at x={landing_x:.1f} (target was x={x_target:.1f}, error={error:+.1f}px, "
              f"next correction={pd.correction:+.2f})")

    return {
        "x_target": x_target,
        "angle_x": angle_x,
        "pd_correction_used": correction_used,
        "landing_x": landing_x,
        "error": error,
    }


def print_recent_pd_feedback(results, window=RECENT_ERROR_WINDOW):
    """
    Prints the mean |error| over the last `window` throws that actually had a
    detected landing -- a quick per-throw signal of whether the PD trim is
    keeping the ball near the target, without waiting for the full run to end.
    """
    recent_errors = [r["error"] for r in results[-window:] if r["error"] is not None]
    if not recent_errors:
        print(f"[PD feedback] no landings detected in the last {window} throw(s) yet.")
        return
    print(f"[PD feedback] mean |error| over last {len(recent_errors)} landed throw(s): "
          f"{np.mean(np.abs(recent_errors)):.1f}px")


def report_pd_feedback(results, window=RECENT_ERROR_WINDOW):
    """
    Compares mean |error| over the first vs. last `window` throws with a
    detected landing, to check whether the PD trim is actually converging
    (shrinking error) over the run -- the same first-vs-last idea as
    reporting.report_learning() for the CMAC, applied to landing accuracy.
    """
    errors = [r["error"] for r in results if r["error"] is not None]
    if len(errors) < 2 * window:
        print(f"[PD feedback] not enough landed throws for a first-vs-last comparison "
              f"(have {len(errors)}, need >= {2 * window}).")
        return

    mean_abs_first = np.mean(np.abs(errors[:window]))
    mean_abs_last = np.mean(np.abs(errors[-window:]))
    print(f"[PD feedback] mean |error| first {window} landed throws: {mean_abs_first:.1f}px")
    print(f"[PD feedback] mean |error| last {window} landed throws:  {mean_abs_last:.1f}px")
    print("[PD feedback] converging:", "yes" if mean_abs_last < mean_abs_first else "no improvement yet")


def plot_pd_feedback(results):
    """Plots landing error and the PD correction that produced it, per throw index."""
    indices = list(range(1, len(results) + 1))
    errors = [r["error"] for r in results]
    corrections = [r["pd_correction_used"] for r in results]

    fig, (ax_err, ax_corr) = plt.subplots(2, 1, figsize=(9, 6), sharex=True)

    landed = [(i, e) for i, e in zip(indices, errors) if e is not None]
    if landed:
        ax_err.plot(*zip(*landed), marker="o")
    ax_err.axhline(0, color="black", linewidth=0.8)
    ax_err.set_ylabel("landing error [px]\n(landing_x - x_target)")
    ax_err.set_title("PD feedback loop: landing error and correction per throw")
    ax_err.grid(True, alpha=0.3)

    ax_corr.plot(indices, corrections, marker="o", color="tab:orange")
    ax_corr.axhline(0, color="black", linewidth=0.8)
    ax_corr.set_xlabel("throw #")
    ax_corr.set_ylabel("PD correction [deg]\n(applied to this throw)")
    ax_corr.grid(True, alpha=0.3)

    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    model = joblib.load(cta.MODEL_PATH)

    cta.initialize_camera()
    cta.initialize_robot()
    cta.go_to_rest()  # start parked in the base position, not wherever initialize_robot left it

    pd = PDController(kp=PD_KP, kd=PD_KD)
    results = []
    while True:
        command = cta.wait_for_next_throw_command()
        if command in ("q", "f"):
            break

        results.append(throw_once(model, pd))
        # throw_and_measure already left the arm at the rest/base position; loop back to wait.
        print_recent_pd_feedback(results)

    if results:
        report_pd_feedback(results)
        plot_pd_feedback(results)

