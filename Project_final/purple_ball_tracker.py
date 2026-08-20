from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

import cv2
import numpy as np


@dataclass
class BallTrackerConfig:
    color_space: str = "LAB"
    low_color: Sequence[int] = (0, 140, 112)
    high_color: Sequence[int] = (136, 147, 125)
    min_area: float = 80.0
    max_area: float = 18000.0
    min_radius: float = 4.0
    max_radius: float = 90.0
    min_circularity: float = 0.45
    min_solidity: float = 0.72
    min_fill_ratio: float = 0.35
    min_confidence: float = 0.55
    morphology_kernel: int = 5
    morphology_iterations: int = 1
    tracking_distance_px: float = 150.0
    confirmation_frames: int = 10
    reacquire_confirmation_frames: int = 3
    confirmation_distance_px: float = 150.0
    confirmation_missed_tolerance_frames: int = 10
    recovery_after_frames: int = 4
    max_lost_frames: int = 30
    max_targets: int = 1
    debug_max_candidates: int = 8

    @property
    def low_array(self) -> np.ndarray:
        return _as_color_bound(self.low_color, "low_color")

    @property
    def high_array(self) -> np.ndarray:
        return _as_color_bound(self.high_color, "high_color")


@dataclass
class BallCandidate:
    contour: np.ndarray
    center: tuple[float, float]
    radius: float
    box: tuple[int, int, int, int]
    area: float
    circularity: float
    solidity: float
    fill_ratio: float
    confidence: float
    accepted: bool
    reject_reasons: list[str] = field(default_factory=list)
    distance_to_prediction: Optional[float] = None


@dataclass
class BallTrack:
    center: tuple[float, float]
    predicted_center: tuple[float, float]
    velocity: tuple[float, float]
    radius: float
    confidence: float
    state: str
    lost_frames: int
    confirmed: bool = False
    confirmation_count: int = 0
    required_confirmation_frames: int = 0
    candidate: Optional[BallCandidate] = None


def _as_color_bound(value: Sequence[int], name: str) -> np.ndarray:
    array = np.asarray(value, dtype=np.uint8)
    if array.shape != (3,):
        raise ValueError(f"{name} must contain exactly three channel values")
    return array


def make_color_mask(frame: np.ndarray, config: BallTrackerConfig) -> np.ndarray:
    color_space = config.color_space.upper()
    if color_space == "LAB":
        converted = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        return cv2.inRange(converted, config.low_array, config.high_array)
    if color_space == "HSV":
        converted = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        low = config.low_array
        high = config.high_array
        if low[0] <= high[0]:
            return cv2.inRange(converted, low, high)

        lower_wrap = cv2.inRange(converted, np.array([0, low[1], low[2]], dtype=np.uint8), high)
        upper_wrap = cv2.inRange(converted, low, np.array([179, high[1], high[2]], dtype=np.uint8))
        return cv2.bitwise_or(lower_wrap, upper_wrap)
    raise ValueError("color_space must be 'LAB' or 'HSV'")


def cleanup_mask(mask: np.ndarray, config: BallTrackerConfig) -> np.ndarray:
    kernel_size = max(1, int(config.morphology_kernel))
    if kernel_size % 2 == 0:
        kernel_size += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    iterations = max(1, int(config.morphology_iterations))
    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=iterations)
    return cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel, iterations=iterations)


def candidate_from_contour(
    contour: np.ndarray,
    config: BallTrackerConfig,
    predicted_center: Optional[tuple[float, float]] = None,
    recovery_mode: bool = False,
) -> BallCandidate:
    area = float(cv2.contourArea(contour))
    perimeter = float(cv2.arcLength(contour, True))
    circularity = 0.0 if perimeter <= 0.0 else float(4.0 * np.pi * area / (perimeter * perimeter))

    hull = cv2.convexHull(contour)
    hull_area = float(cv2.contourArea(hull))
    solidity = 0.0 if hull_area <= 0.0 else area / hull_area

    (center_x, center_y), radius = cv2.minEnclosingCircle(contour)
    circle_area = float(np.pi * radius * radius)
    fill_ratio = 0.0 if circle_area <= 0.0 else area / circle_area
    x, y, width, height = cv2.boundingRect(contour)

    reject_reasons: list[str] = []
    area_min = config.min_area * (0.55 if recovery_mode else 1.0)
    circularity_min = config.min_circularity * (0.65 if recovery_mode else 1.0)
    solidity_min = config.min_solidity * (0.80 if recovery_mode else 1.0)
    fill_min = config.min_fill_ratio * (0.75 if recovery_mode else 1.0)
    radius_min = config.min_radius * (0.70 if recovery_mode else 1.0)
    radius_max = config.max_radius * (1.25 if recovery_mode else 1.0)

    if area < area_min:
        reject_reasons.append(f"area {area:.0f} < {area_min:.0f}")
    if area > config.max_area:
        reject_reasons.append(f"area {area:.0f} > {config.max_area:.0f}")
    if radius < radius_min:
        reject_reasons.append(f"radius {radius:.1f} < {radius_min:.1f}")
    if radius > radius_max:
        reject_reasons.append(f"radius {radius:.1f} > {radius_max:.1f}")
    if circularity < circularity_min:
        reject_reasons.append(f"circ {circularity:.2f} < {circularity_min:.2f}")
    if solidity < solidity_min:
        reject_reasons.append(f"solidity {solidity:.2f} < {solidity_min:.2f}")
    if fill_ratio < fill_min:
        reject_reasons.append(f"fill {fill_ratio:.2f} < {fill_min:.2f}")

    distance_to_prediction = None
    tracking_score = 1.0
    if predicted_center is not None:
        distance_to_prediction = float(np.hypot(center_x - predicted_center[0], center_y - predicted_center[1]))
        search_radius = config.tracking_distance_px * (2.0 if recovery_mode else 1.0)
        tracking_score = max(0.0, 1.0 - distance_to_prediction / max(1.0, search_radius))
        if distance_to_prediction > search_radius:
            reject_reasons.append(f"pred dist {distance_to_prediction:.0f} > {search_radius:.0f}")

    area_score = min(1.0, area / max(area_min * 4.0, 1.0))
    radius_score = min(1.0, radius / max(radius_min * 3.0, 1.0))
    shape_score = np.clip((circularity + solidity + fill_ratio) / 3.0, 0.0, 1.0)
    confidence = float(0.35 * shape_score + 0.25 * area_score + 0.20 * radius_score + 0.20 * tracking_score)
    accepted = not reject_reasons and confidence >= config.min_confidence
    if not accepted and not reject_reasons:
        reject_reasons.append(f"conf {confidence:.2f} < {config.min_confidence:.2f}")

    return BallCandidate(
        contour=contour,
        center=(float(center_x), float(center_y)),
        radius=float(radius),
        box=(int(x), int(y), int(width), int(height)),
        area=area,
        circularity=float(circularity),
        solidity=float(solidity),
        fill_ratio=float(fill_ratio),
        confidence=confidence,
        accepted=accepted,
        reject_reasons=reject_reasons,
        distance_to_prediction=distance_to_prediction,
    )


def find_ball_candidates(
    frame: np.ndarray,
    config: BallTrackerConfig,
    predicted_center: Optional[tuple[float, float]] = None,
    recovery_mode: bool = False,
) -> tuple[list[BallCandidate], np.ndarray]:
    mask = cleanup_mask(make_color_mask(frame, config), config)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = [
        candidate_from_contour(contour, config, predicted_center, recovery_mode)
        for contour in contours
        if cv2.contourArea(contour) > 0
    ]
    candidates.sort(key=lambda item: item.confidence, reverse=True)
    enforce_max_targets(candidates, config.max_targets)
    return candidates, mask


def enforce_max_targets(candidates: Sequence[BallCandidate], max_targets: int = 1) -> None:
    """Keep at most N accepted candidates after confidence sorting."""
    accepted_seen = 0
    for candidate in candidates:
        if not candidate.accepted:
            continue
        accepted_seen += 1
        if accepted_seen > max_targets:
            candidate.accepted = False
            candidate.reject_reasons.append(f"extra target > max_targets {max_targets}")


class PurpleBallTracker:
    def __init__(self, config: Optional[BallTrackerConfig] = None) -> None:
        self.config = config or BallTrackerConfig()
        self.kalman = cv2.KalmanFilter(4, 2)
        self.kalman.measurementMatrix = np.array(
            [[1, 0, 0, 0], [0, 1, 0, 0]],
            dtype=np.float32,
        )
        self.kalman.processNoiseCov = np.eye(4, dtype=np.float32) * 0.03
        self.kalman.measurementNoiseCov = np.eye(2, dtype=np.float32) * 6.0
        self.kalman.errorCovPost = np.eye(4, dtype=np.float32)
        self.initialized = False
        self.lost_frames = 0
        self.confirmation_count = 0
        self.confirmed = False
        self.ever_confirmed = False
        self.last_track: Optional[BallTrack] = None
        self.path: list[tuple[int, int]] = []

    def reset(self) -> None:
        self.initialized = False
        self.lost_frames = 0
        self.confirmation_count = 0
        self.confirmed = False
        self.ever_confirmed = False
        self.last_track = None
        self.path.clear()

    def _predict(self, dt: float) -> Optional[tuple[float, float]]:
        if not self.initialized:
            return None
        self.kalman.transitionMatrix = np.array(
            [[1, 0, dt, 0], [0, 1, 0, dt], [0, 0, 1, 0], [0, 0, 0, 1]],
            dtype=np.float32,
        )
        prediction = self.kalman.predict()
        return float(prediction[0]), float(prediction[1])

    def _correct(self, center: tuple[float, float]) -> np.ndarray:
        measurement = np.array([[np.float32(center[0])], [np.float32(center[1])]])
        if not self.initialized:
            self.kalman.statePost = np.array(
                [[np.float32(center[0])], [np.float32(center[1])], [0.0], [0.0]],
                dtype=np.float32,
            )
            self.initialized = True
            return self.kalman.statePost
        return self.kalman.correct(measurement)

    def update(self, frame: np.ndarray, dt: float = 1.0 / 60.0) -> tuple[Optional[BallTrack], list[BallCandidate], np.ndarray]:
        predicted_center = self._predict(dt)
        recovery_mode = self.lost_frames >= self.config.recovery_after_frames
        candidates, mask = find_ball_candidates(frame, self.config, predicted_center, recovery_mode)
        accepted = [candidate for candidate in candidates if candidate.accepted]

        if accepted:
            candidate = accepted[0]
            was_initialized = self.initialized
            was_consistent = self._is_consistent_with_prediction(candidate)
            state_post = self._correct(candidate.center)
            self.lost_frames = 0
            if not was_initialized:
                self.confirmation_count = 1
            elif was_consistent:
                self.confirmation_count += 1
            else:
                self.confirmation_count = 1

            required_confirmation = self._required_confirmation_frames()
            self.confirmed = self.confirmation_count >= required_confirmation
            if self.confirmed:
                self.ever_confirmed = True
            center = (float(state_post[0]), float(state_post[1]))
            velocity = (float(state_post[2]), float(state_post[3]))
            if self.confirmed:
                state = "DETECTED" if not recovery_mode else "RECOVERED"
            else:
                state = f"CONFIRMING {self.confirmation_count}/{required_confirmation}"
            track = BallTrack(
                center=center,
                predicted_center=predicted_center or candidate.center,
                velocity=velocity,
                radius=candidate.radius,
                confidence=candidate.confidence,
                state=state,
                lost_frames=0,
                confirmed=self.confirmed,
                confirmation_count=self.confirmation_count,
                required_confirmation_frames=required_confirmation,
                candidate=candidate,
            )
            self.path.append((int(round(center[0])), int(round(center[1]))))
            self.path = self.path[-80:]
            self.last_track = track
            return track, candidates, mask

        self.lost_frames += 1
        missed_tolerance = max(0, int(self.config.confirmation_missed_tolerance_frames))
        if self.lost_frames >= missed_tolerance:
            self.confirmation_count = 0
            self.confirmed = False
        if not self.initialized or predicted_center is None or self.lost_frames > self.config.max_lost_frames:
            if self.lost_frames > self.config.max_lost_frames:
                self.reset()
            return None, candidates, mask

        velocity = (float(self.kalman.statePost[2]), float(self.kalman.statePost[3]))
        track = BallTrack(
            center=predicted_center,
            predicted_center=predicted_center,
            velocity=velocity,
            radius=self.last_track.radius if self.last_track else 0.0,
            confidence=0.0,
            state="RECOVERY" if recovery_mode else "TRACKED",
            lost_frames=self.lost_frames,
            confirmed=self.confirmed,
            confirmation_count=self.confirmation_count,
            required_confirmation_frames=self._required_confirmation_frames(),
            candidate=None,
        )
        self.last_track = track
        return track, candidates, mask

    def _required_confirmation_frames(self) -> int:
        if self.ever_confirmed:
            return max(1, int(self.config.reacquire_confirmation_frames))
        return max(1, int(self.config.confirmation_frames))

    def _is_consistent_with_prediction(self, candidate: BallCandidate) -> bool:
        if candidate.distance_to_prediction is None:
            return True
        max_distance = max(1.0, float(self.config.confirmation_distance_px))
        return candidate.distance_to_prediction <= max_distance


def draw_debug_overlay(
    frame: np.ndarray,
    track: Optional[BallTrack],
    candidates: Sequence[BallCandidate],
    mask: Optional[np.ndarray] = None,
    config: Optional[BallTrackerConfig] = None,
    show_mask: bool = False,
) -> np.ndarray:
    config = config or BallTrackerConfig()
    overlay = frame.copy()

    if show_mask and mask is not None:
        mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        overlay = cv2.addWeighted(overlay, 0.65, mask_bgr, 0.35, 0.0)

    track_color = _track_state_color(track.state) if track is not None else None
    for index, candidate in enumerate(candidates[: config.debug_max_candidates], start=1):
        is_active_track_candidate = track is not None and candidate is track.candidate
        if candidate.accepted:
            color = track_color if is_active_track_candidate and track_color is not None else (0, 220, 0)
        else:
            color = (0, 0, 255)
        x, y, width, height = candidate.box
        cv2.rectangle(overlay, (x, y), (x + width, y + height), color, 2)
        cv2.circle(overlay, (int(candidate.center[0]), int(candidate.center[1])), int(candidate.radius), color, 1)
        reason = track.state if is_active_track_candidate else ("accepted" if candidate.accepted else candidate.reject_reasons[0])
        label = f"{index} {candidate.confidence:.2f} {reason}"
        _draw_text(overlay, label, (x, max(18, y - 6)), color)

    if track is not None:
        center = (int(round(track.center[0])), int(round(track.center[1])))
        predicted = (int(round(track.predicted_center[0])), int(round(track.predicted_center[1])))
        color = track_color or (255, 255, 255)
        cv2.drawMarker(overlay, predicted, (0, 255, 255), cv2.MARKER_CROSS, 18, 2)
        cv2.circle(overlay, center, max(4, int(round(track.radius))), color, 2)
        cv2.circle(overlay, center, 3, (0, 255, 255), -1)

    if track is not None and hasattr(track, "state"):
        required_confirmation = track.required_confirmation_frames or config.confirmation_frames
        status = (
            f"{track.state} conf={track.confidence:.2f} "
            f"confirm={track.confirmation_count}/{required_confirmation} "
            f"lost={track.lost_frames}/{config.confirmation_missed_tolerance_frames}"
        )
    else:
        status = "NO BALL"
    panel_lines = [
        status,
        f"candidates={len(candidates)} min_area={config.min_area:.0f} circ>={config.min_circularity:.2f} sol>={config.min_solidity:.2f}",
        "ESC stop | d debug | m mask | r reset | c print config",
    ]
    _draw_panel(overlay, panel_lines, (10, 10))
    return overlay


def draw_path(frame: np.ndarray, path: Sequence[tuple[int, int]]) -> np.ndarray:
    if len(path) < 2:
        return frame
    for prev, cur in zip(path[:-1], path[1:]):
        cv2.line(frame, prev, cur, (255, 255, 0), 2, cv2.LINE_AA)
    return frame


def _track_state_color(state: str) -> tuple[int, int, int]:
    state_upper = state.upper()
    if state_upper.startswith("CONFIRMING"):
        return (0, 220, 255)
    if state_upper == "DETECTED":
        return (0, 220, 0)
    if state_upper == "TRACKED":
        return (255, 180, 0)
    if state_upper == "RECOVERY":
        return (0, 140, 255)
    if state_upper == "RECOVERED":
        return (255, 0, 255)
    return (255, 255, 255)


def _draw_text(frame: np.ndarray, text: str, origin: tuple[int, int], color: tuple[int, int, int]) -> None:
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.45
    thickness = 1
    cv2.putText(frame, text, origin, font, scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
    cv2.putText(frame, text, origin, font, scale, color, thickness, cv2.LINE_AA)


def _draw_panel(frame: np.ndarray, lines: Sequence[str], origin: tuple[int, int]) -> None:
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.52
    thickness = 1
    margin = 8
    line_height = 22
    width = max(cv2.getTextSize(line, font, scale, thickness)[0][0] for line in lines)
    height = margin * 2 + line_height * len(lines)
    x, y = origin
    cv2.rectangle(frame, (x, y), (x + width + margin * 2, y + height), (0, 0, 0), -1)
    for index, line in enumerate(lines):
        cv2.putText(
            frame,
            line,
            (x + margin, y + margin + 16 + index * line_height),
            font,
            scale,
            (255, 255, 255),
            thickness,
            cv2.LINE_AA,
        )
