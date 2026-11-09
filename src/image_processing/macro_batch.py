"""Compatibility entry point for the existing ImageJ batch GUI."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from p1_ImageProcessing_macro import BatchWorker, ImageJBatchGUI  # noqa: E402,F401

__all__ = ["BatchWorker", "ImageJBatchGUI"]
