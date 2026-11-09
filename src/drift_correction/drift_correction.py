"""Compatibility entry point for drift correction."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from p2_drift_correction_v3IB import main, list_images, pick_roi, to_uint8_contrast  # noqa: E402,F401

__all__ = ["main", "list_images", "pick_roi", "to_uint8_contrast"]
