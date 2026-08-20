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
import numpy as np
import pyaudio

import camera_to_angle as cta

# Microphone-based impact detection. AUDIO_IMPACT_THRESHOLD is the RMS level
# (16-bit PCM) that counts as a "thud" -- there's no way to derive this from
# code, calibrate it with print_mic_levels() below and tap the table.
AUDIO_RATE = 44100
AUDIO_CHUNK = 1024
AUDIO_IMPACT_THRESHOLD = 150.0
IMPACT_TIMEOUT = 5.0  # seconds to listen for an impact before giving up


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


def throw_once(model):
    """Detects the target, throws at it, and prints timing/landing info for one throw."""
    t_target_detected = time.time()
    x_target = cta.get_target_x()
    print(f"Target detected at x={x_target:.1f}")

    angle_x, y_backswing, y_release = cta.predict_throw(x_target, model)
    print(f"Predicted throw: angle_x={angle_x:.1f} y_backswing={y_backswing:.1f} y_release={y_release:.1f}")

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
    landing_x = cta.throw_and_measure(angle_x, y_backswing, y_release, on_release=mark_release)

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
        print("Could not detect where the ball landed (camera).")
    else:
        print(f"Ball landed at x={landing_x:.1f} (target was x={x_target:.1f}, error={landing_x - x_target:+.1f}px)")


if __name__ == "__main__":
    model = joblib.load(cta.MODEL_PATH)

    cta.initialize_camera()
    cta.initialize_robot()
    cta.go_to_rest()  # start parked in the base position, not wherever initialize_robot left it

    while True:
        command = cta.wait_for_next_throw_command()
        if command in ("q", "f"):
            break

        throw_once(model)
        # throw_and_measure already left the arm at the rest/base position; loop back to wait.

