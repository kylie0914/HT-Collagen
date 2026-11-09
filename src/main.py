"""Stable application entry point for the HT-Collagen desktop GUI.

Run from any working directory with: python -m src.main
The existing analysis modules remain at repository root for compatibility.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from src.image_processing.macro_batch import ImageJBatchGUI
from src.drift_correction.drift_correction import main as drift_correction_main
from src.density_analysis.density_tracking import MainDensityWindow
from src.pivlab.pivlab_launcher import run_pivlab_flow

RESOURCES = ROOT / "resources"


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.imageproc_window = None
        self.density_window = None
        self.pivlab_exe_path = None
        self.setWindowTitle("HT-Collagen | Fiber Migration Analysis")
        self.resize(820, 560)
        self._build_ui()

    def _build_ui(self):
        logo = QLabel()
        logo_path = RESOURCES / "0_CSB_logo_v1.png"
        pixmap = QPixmap(str(logo_path))
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaled(260, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        title = QLabel("HT-Collagen")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        description = QLabel(
            "Fiber migration analysis workflow\n\n"
            "1. ImageJ-based image preprocessing\n"
            "2. FFT-based drift correction\n"
            "3. Density heatmap and difference analysis\n"
            "4. Launch external PIVlab for optical-flow analysis"
        )
        description.setWordWrap(True)

        self.image_button = QPushButton("1. Image Processing")
        self.drift_button = QPushButton("2. Drift Correction")
        self.density_button = QPushButton("3. Density Analysis")
        self.piv_button = QPushButton("4. Launch PIVlab")
        for button in (self.image_button, self.drift_button, self.density_button, self.piv_button):
            button.setMinimumHeight(48)

        self.image_button.clicked.connect(self.open_image_processing)
        self.drift_button.clicked.connect(self.run_drift_correction)
        self.density_button.clicked.connect(self.open_density_analysis)
        self.piv_button.clicked.connect(self.open_pivlab)

        left = QVBoxLayout()
        left.addWidget(logo)
        left.addWidget(title)
        left.addWidget(description)
        left.addStretch()

        right = QVBoxLayout()
        right.addWidget(QLabel("Analysis workflow"))
        right.addWidget(self.image_button)
        right.addWidget(self.drift_button)
        right.addWidget(self.density_button)
        right.addWidget(self.piv_button)
        right.addStretch()

        layout = QHBoxLayout()
        layout.addLayout(left, 2)
        layout.addLayout(right, 3)
        self.setLayout(layout)

    def open_image_processing(self):
        if self.imageproc_window is not None and self.imageproc_window.isVisible():
            self.imageproc_window.raise_()
            self.imageproc_window.activateWindow()
            return
        self.imageproc_window = ImageJBatchGUI()
        self.imageproc_window.show()

    def run_drift_correction(self):
        try:
            drift_correction_main()
        except Exception as exc:
            QMessageBox.critical(self, "Drift Correction Error", str(exc))

    def open_density_analysis(self):
        if self.density_window is not None and self.density_window.isVisible():
            self.density_window.raise_()
            self.density_window.activateWindow()
            return
        self.density_window = MainDensityWindow()
        self.density_window.show()

    def open_pivlab(self):
        try:
            self.pivlab_exe_path, _ = run_pivlab_flow(
                parent=self,
                exe_path=self.pivlab_exe_path,
                ask_input_dir=True,
            )
        except Exception as exc:
            QMessageBox.critical(self, "PIVlab launch failed", str(exc))


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
