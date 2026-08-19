"""
Loads the trained model, detects the target's current position with the
camera, and throws the ball at it.

Also times the throw with the microphone: since the camera-based landing
detection isn't reliable yet, we listen for the "thud" of the ball hitting
the table and use that instant as the landing time instead.
"""
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


def _chunk_rms(stream):
    data = stream.read(AUDIO_CHUNK, exception_on_overflow=False)
    samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
    return float(np.sqrt(np.mean(samples ** 2)))


def print_mic_levels(duration=10.0):
    """Prints live microphone RMS levels -- use this to pick AUDIO_IMPACT_THRESHOLD."""
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


def detect_impact(timeout=IMPACT_TIMEOUT):
    """
    Listens to the default microphone and returns the time.time() timestamp
    of the first chunk whose RMS level crosses AUDIO_IMPACT_THRESHOLD.
    Returns None if nothing crosses it before `timeout`.
    """
    pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16, channels=1, rate=AUDIO_RATE, input=True, frames_per_buffer=AUDIO_CHUNK)
    try:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if _chunk_rms(stream) > AUDIO_IMPACT_THRESHOLD:
                return time.time()
        return None
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()


if __name__ == "__main__":
    model = joblib.load(cta.MODEL_PATH)

    cta.initialize_camera()
    cta.initialize_robot()

    t_target_detected = time.time()
    x_target = cta.get_target_x()
    print(f"Target detected at x={x_target:.1f}")

    angle_x, y_backswing, y_release = cta.predict_throw(x_target, model)
    print(f"Predicted throw: angle_x={angle_x:.1f} y_backswing={y_backswing:.1f} y_release={y_release:.1f}")

    impact_result = {}
    listener = threading.Thread(target=lambda: impact_result.update(t=detect_impact()))
    listener.start()

    landing_x = cta.throw_and_measure(angle_x, y_backswing, y_release)

    listener.join()
    impact_time = impact_result.get("t")

    if landing_x is None:
        print("Could not detect where the ball landed (camera).")
    else:
        print(f"Ball landed at x={landing_x:.1f} (target was x={x_target:.1f}, error={landing_x - x_target:+.1f}px)")

    if impact_time is None:
        print("Could not detect the ball's impact sound (microphone).")
    else:
        time_of_flight = impact_time - t_target_detected
        print(f"Time of flight (target detected -> ball landed, via mic): {time_of_flight:.3f}s")
