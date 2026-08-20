import cv2
import numpy as np

from purple_ball_tracker import BallTrackerConfig, PurpleBallTracker, find_ball_candidates


def bgr_from_lab(lab):
    pixel = np.array([[lab]], dtype=np.uint8)
    return tuple(int(value) for value in cv2.cvtColor(pixel, cv2.COLOR_LAB2BGR)[0, 0])


def make_frame():
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    purple_bgr = bgr_from_lab([68, 144, 118])
    cv2.circle(frame, (120, 90), 18, purple_bgr, -1)
    return frame


def test_detects_round_purple_ball():
    frame = make_frame()
    config = BallTrackerConfig(
        low_color=(0, 140, 112),
        high_color=(136, 147, 125),
        min_area=100,
        min_radius=8,
        min_circularity=0.6,
        min_solidity=0.8,
    )

    candidates, _ = find_ball_candidates(frame, config)

    assert candidates
    assert candidates[0].accepted
    assert abs(candidates[0].center[0] - 120) < 2
    assert abs(candidates[0].center[1] - 90) < 2


def test_rejects_non_circular_purple_blob():
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    purple_bgr = bgr_from_lab([68, 144, 118])
    cv2.rectangle(frame, (40, 40), (180, 55), purple_bgr, -1)
    config = BallTrackerConfig(
        low_color=(0, 140, 112),
        high_color=(136, 147, 125),
        min_area=100,
        min_radius=4,
        min_circularity=0.65,
        min_solidity=0.8,
    )

    candidates, _ = find_ball_candidates(frame, config)

    assert candidates
    assert not candidates[0].accepted
    assert any("circ" in reason for reason in candidates[0].reject_reasons)


def test_accepts_at_most_one_target():
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    purple_bgr = bgr_from_lab([68, 144, 118])
    cv2.circle(frame, (90, 90), 18, purple_bgr, -1)
    cv2.circle(frame, (210, 90), 18, purple_bgr, -1)
    config = BallTrackerConfig(
        low_color=(0, 140, 112),
        high_color=(136, 147, 125),
        min_area=100,
        min_radius=8,
        min_circularity=0.6,
        min_solidity=0.8,
        max_targets=1,
    )

    candidates, _ = find_ball_candidates(frame, config)
    accepted = [candidate for candidate in candidates if candidate.accepted]
    rejected = [candidate for candidate in candidates if not candidate.accepted]

    assert len(accepted) == 1
    assert any("extra target" in reason for candidate in rejected for reason in candidate.reject_reasons)


def test_tracker_predicts_during_short_loss():
    config = BallTrackerConfig(
        low_color=(0, 140, 112),
        high_color=(136, 147, 125),
        min_area=100,
        max_lost_frames=5,
        confirmation_frames=1,
    )
    tracker = PurpleBallTracker(config)

    track, _, _ = tracker.update(make_frame(), dt=1.0 / 60.0)
    assert track is not None
    assert track.state == "DETECTED"

    empty_frame = np.zeros((240, 320, 3), dtype=np.uint8)
    track, _, _ = tracker.update(empty_frame, dt=1.0 / 60.0)

    assert track is not None
    assert track.state == "TRACKED"
    assert track.lost_frames == 1


def test_tracker_requires_ten_consecutive_confirming_frames():
    config = BallTrackerConfig(
        low_color=(0, 140, 112),
        high_color=(136, 147, 125),
        min_area=100,
        confirmation_frames=10,
        confirmation_distance_px=30,
    )
    tracker = PurpleBallTracker(config)

    for index in range(9):
        track, _, _ = tracker.update(make_frame(), dt=1.0 / 60.0)
        assert track is not None
        assert not track.confirmed
        assert track.confirmation_count == index + 1
        assert track.state == f"CONFIRMING {index + 1}/10"

    track, _, _ = tracker.update(make_frame(), dt=1.0 / 60.0)

    assert track is not None
    assert track.confirmed
    assert track.confirmation_count == 10
    assert track.state == "DETECTED"


def test_confirmation_survives_short_missed_run_and_clears_after_tolerance():
    config = BallTrackerConfig(
        low_color=(0, 140, 112),
        high_color=(136, 147, 125),
        min_area=100,
        confirmation_frames=10,
        confirmation_distance_px=30,
        confirmation_missed_tolerance_frames=10,
        max_lost_frames=20,
    )
    tracker = PurpleBallTracker(config)

    for _ in range(5):
        track, _, _ = tracker.update(make_frame(), dt=1.0 / 60.0)

    assert track is not None
    assert track.confirmation_count == 5
    assert not track.confirmed

    empty_frame = np.zeros((240, 320, 3), dtype=np.uint8)
    for _ in range(9):
        track, _, _ = tracker.update(empty_frame, dt=1.0 / 60.0)
        assert track is not None
        assert track.confirmation_count == 5

    track, _, _ = tracker.update(empty_frame, dt=1.0 / 60.0)

    assert track is not None
    assert track.confirmation_count == 0
    assert not track.confirmed


def test_reacquire_uses_shorter_confirmation_after_initial_lock():
    config = BallTrackerConfig(
        low_color=(0, 140, 112),
        high_color=(136, 147, 125),
        min_area=100,
        confirmation_frames=5,
        reacquire_confirmation_frames=3,
        confirmation_distance_px=30,
        confirmation_missed_tolerance_frames=1,
        max_lost_frames=20,
    )
    tracker = PurpleBallTracker(config)

    for _ in range(5):
        track, _, _ = tracker.update(make_frame(), dt=1.0 / 60.0)

    assert track is not None
    assert track.confirmed
    assert track.state == "DETECTED"

    empty_frame = np.zeros((240, 320, 3), dtype=np.uint8)
    track, _, _ = tracker.update(empty_frame, dt=1.0 / 60.0)

    assert track is not None
    assert not track.confirmed
    assert track.confirmation_count == 0

    for index in range(2):
        track, _, _ = tracker.update(make_frame(), dt=1.0 / 60.0)
        assert track is not None
        assert not track.confirmed
        assert track.state == f"CONFIRMING {index + 1}/3"

    track, _, _ = tracker.update(make_frame(), dt=1.0 / 60.0)

    assert track is not None
    assert track.confirmed
    assert track.confirmation_count == 3
    assert track.required_confirmation_frames == 3
    assert track.state == "DETECTED"
