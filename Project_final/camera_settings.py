from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import cv2


SETTINGS_PATH = Path(__file__).resolve().parent / "camera_control_settings.json"


def load_camera_settings(path: Optional[Path] = None) -> Optional[dict[str, Any]]:
    settings_path = path or SETTINGS_PATH
    if not settings_path.exists():
        return None
    return json.loads(settings_path.read_text(encoding="utf-8"))


def save_camera_settings(settings: dict[str, Any], path: Optional[Path] = None) -> Path:
    settings_path = path or SETTINGS_PATH
    settings_path.write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return settings_path


def _get_prop(capture: cv2.VideoCapture, prop_id: int) -> Optional[float]:
    if prop_id < 0:
        return None
    try:
        return float(capture.get(prop_id))
    except Exception:
        return None


def _set_prop(capture: cv2.VideoCapture, prop_id: int, value: Optional[float]) -> tuple[bool, Optional[float], Optional[float]]:
    if value is None or prop_id < 0:
        return False, None, None
    before = _get_prop(capture, prop_id)
    try:
        ok = bool(capture.set(prop_id, float(value)))
    except Exception:
        ok = False
    after = _get_prop(capture, prop_id)
    return ok, before, after


def read_webcam_settings(capture: cv2.VideoCapture) -> dict[str, Optional[float]]:
    return {
        "auto_exposure_value": _get_prop(capture, getattr(cv2, "CAP_PROP_AUTO_EXPOSURE", -1)),
        "exposure": _get_prop(capture, cv2.CAP_PROP_EXPOSURE),
        "gain": _get_prop(capture, cv2.CAP_PROP_GAIN),
        "auto_wb_value": _get_prop(capture, getattr(cv2, "CAP_PROP_AUTO_WB", -1)),
        "white_balance": _get_prop(capture, getattr(cv2, "CAP_PROP_WB_TEMPERATURE", -1)),
        "brightness": _get_prop(capture, cv2.CAP_PROP_BRIGHTNESS),
        "contrast": _get_prop(capture, cv2.CAP_PROP_CONTRAST),
        "saturation": _get_prop(capture, cv2.CAP_PROP_SATURATION),
    }


def apply_webcam_settings(capture: cv2.VideoCapture, settings: dict[str, Any], verbose: bool = True) -> None:
    if verbose:
        print("Applying saved webcam settings:")

    if "auto_exposure" in settings and hasattr(cv2, "CAP_PROP_AUTO_EXPOSURE"):
        # V4L2 convention: 3.0 is auto/aperture-priority, 1.0 is manual.
        value = 3.0 if settings["auto_exposure"] else 1.0
        _print_set_result("AUTO_EXPOSURE", value, _set_prop(capture, cv2.CAP_PROP_AUTO_EXPOSURE, value), verbose)

    if not settings.get("auto_exposure", True):
        _print_set_result("EXPOSURE", settings.get("exposure"), _set_prop(capture, cv2.CAP_PROP_EXPOSURE, settings.get("exposure")), verbose)

    if settings.get("gain") is not None:
        _print_set_result("GAIN", settings.get("gain"), _set_prop(capture, cv2.CAP_PROP_GAIN, settings.get("gain")), verbose)

    if "auto_wb" in settings and hasattr(cv2, "CAP_PROP_AUTO_WB"):
        value = 1.0 if settings["auto_wb"] else 0.0
        _print_set_result("AUTO_WB", value, _set_prop(capture, cv2.CAP_PROP_AUTO_WB, value), verbose)

    if not settings.get("auto_wb", True) and hasattr(cv2, "CAP_PROP_WB_TEMPERATURE"):
        _print_set_result(
            "WB_TEMPERATURE",
            settings.get("white_balance"),
            _set_prop(capture, cv2.CAP_PROP_WB_TEMPERATURE, settings.get("white_balance")),
            verbose,
        )

    for label, prop_id, key in [
        ("BRIGHTNESS", cv2.CAP_PROP_BRIGHTNESS, "brightness"),
        ("CONTRAST", cv2.CAP_PROP_CONTRAST, "contrast"),
        ("SATURATION", cv2.CAP_PROP_SATURATION, "saturation"),
    ]:
        if settings.get(key) is not None:
            _print_set_result(label, settings.get(key), _set_prop(capture, prop_id, settings.get(key)), verbose)


def _print_set_result(
    label: str,
    requested: Any,
    result: tuple[bool, Optional[float], Optional[float]],
    verbose: bool,
) -> None:
    if not verbose:
        return
    ok, before, after = result
    print(f"  {label}: before={_fmt(before)} requested={_fmt(requested)} after={_fmt(after)} ok={ok}")


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return str(value)
