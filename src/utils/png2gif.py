"""Compatibility entry point for the PNG-to-GIF/MP4 exporter."""
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]


def main():
    runpy.run_path(str(ROOT / "png2gif.py"), run_name="__main__")


if __name__ == "__main__":
    main()
