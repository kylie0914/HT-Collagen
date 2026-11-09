"""Compatibility entry point for launching an external PIVlab installation."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from p4_PIVlab import launch_pivlab, run_pivlab_flow, select_input_dir, select_pivlab_exe  # noqa: E402,F401

__all__ = ["launch_pivlab", "run_pivlab_flow", "select_input_dir", "select_pivlab_exe"]
