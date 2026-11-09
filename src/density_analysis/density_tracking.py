"""Compatibility entry point for the existing density-analysis GUI."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from p3_density_tracking import MainDensityWindow, convert_all_to_8bit_png, densityEstimation, densityTracking  # noqa: E402,F401

__all__ = ["MainDensityWindow", "convert_all_to_8bit_png", "densityEstimation", "densityTracking"]
