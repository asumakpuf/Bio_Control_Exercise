import cv2
import numpy as np

import camera_to_angle as cta

FRAME_WIDTH = 220
FRAME_HEIGHT = 200

TARGET_Y_TOP = 90
TARGET_HEIGHT = 20

BALL_SIZE = 20
BALL_ABOVE = (40, 20)     # (x, y) well above the target line
BALL_BELOW = (160, 160)   # (x, y) well below the target line


def _lab_paint_color(low, high):
    """BGR color whose LAB value (OpenCV's 0-255 LAB convention) sits at the
    midpoint of [low, high], so painting it reproduces a real in-threshold color."""
    mid = ((np.array(low, dtype=np.float64) + np.array(high, dtype=np.float64)) / 2).astype(np.uint8)
    bgr = cv2.cvtColor(mid.reshape(1, 1, 3), cv2.COLOR_LAB2BGR)[0, 0]
    return tuple(int(c) for c in bgr)


OBJECT_COLOR_BGR = _lab_paint_color(cta.OBJECT_LOW, cta.OBJECT_HIGH)
TARGET_COLOR_BGR = _lab_paint_color(cta.TARGET_LOW, cta.TARGET_HIGH)


def blank_frame():
    return np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)


def paint_target_line(frame):
    frame[TARGET_Y_TOP:TARGET_Y_TOP + TARGET_HEIGHT, :] = TARGET_COLOR_BGR
    return frame


def paint_ball(frame, x, y):
    frame[y:y + BALL_SIZE, x:x + BALL_SIZE] = OBJECT_COLOR_BGR
    return frame


def frame_with_ball(x, y):
    return paint_ball(paint_target_line(blank_frame()), x, y)


class FrameFeed:
    """Feeds a fixed list of frames, then repeats the last one forever."""

    def __init__(self, frames):
        self.frames = frames
        self.i = 0

    def __call__(self, _cam):
        frame = self.frames[min(self.i, len(self.frames) - 1)]
        self.i += 1
        return frame


def run_with_frames(frames):
    original_capture = cta.ct.capture_image
    cta.ct.capture_image = FrameFeed(frames)
    try:
        return cta.wait_for_landing_x()
    finally:
        cta.ct.capture_image = original_capture


def test_color_calibration_sanity():
    """Synthetic paint colors must actually fall inside the real OBJECT/TARGET thresholds."""
    frame = frame_with_ball(*BALL_ABOVE)

    target = cta.get_target_bounding_box_coordinates(frame, cta._target_model)
    ball = cta.get_object_coordinates(frame, cta._object_model)

    assert target is not None, "synthetic target color wasn't detected -- check TARGET_LOW/HIGH"
    assert ball is not None, "synthetic ball color wasn't detected -- check OBJECT_LOW/HIGH"
    print("test_color_calibration_sanity: OK")


def test_detects_crossing_and_returns_landing_x():
    above = frame_with_ball(*BALL_ABOVE)
    below = frame_with_ball(*BALL_BELOW)

    x = run_with_frames([above, below])

    expected_x = BALL_BELOW[0] + BALL_SIZE / 2
    assert x is not None, "expected a crossing to be detected"
    assert abs(x - expected_x) < 1e-6, f"expected landing x={expected_x}, got {x}"
    print(f"test_detects_crossing_and_returns_landing_x: OK (x={x})")


def test_no_crossing_times_out_to_none():
    only_above = [frame_with_ball(*BALL_ABOVE) for _ in range(3)]

    original_timeout = cta.CATCH_TIMEOUT
    cta.CATCH_TIMEOUT = 0.2  # keep the test fast
    try:
        x = run_with_frames(only_above)
    finally:
        cta.CATCH_TIMEOUT = original_timeout

    assert x is None, f"expected no crossing (None), got {x}"
    print("test_no_crossing_times_out_to_none: OK")


def test_dropped_frame_before_ball_seen_does_not_break_detection():

    empty = paint_target_line(blank_frame())
    above = frame_with_ball(*BALL_ABOVE)
    below = frame_with_ball(*BALL_BELOW)

    x = run_with_frames([empty, above, below])

    expected_x = BALL_BELOW[0] + BALL_SIZE / 2
    assert x is not None, "expected a crossing to still be detected after a dropped frame"
    assert abs(x - expected_x) < 1e-6, f"expected landing x={expected_x}, got {x}"
    print(f"test_dropped_frame_before_ball_seen_does_not_break_detection: OK (x={x})")


if __name__ == "__main__":
    test_color_calibration_sanity()
    test_detects_crossing_and_returns_landing_x()
    test_no_crossing_times_out_to_none()
    test_dropped_frame_before_ball_seen_does_not_break_detection()
    print("\nAll offline line-crossing tests passed.")
