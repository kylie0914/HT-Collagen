"""
[ImageJ 매크로 배치 실행 GUI - 프리뷰 없음]
- 버튼 클릭 → 폴더 선택 → 폴더 내 이미지 일괄 처리 → TIF 저장
- 파라미터: rolling, thr1, thr2, maxval (기본값: 10, 11, 13285, 65535)

설치:
  conda install -c conda-forge pyimagej openjdk
  (또는) pip install pyimagej

지원 포맷: .tif .tiff .png .jpg .jpeg
출력 위치: <입력폴더>/imgj_proc/<원본이름>_imgProc.tif
"""

import os, re
import glob
from typing import Iterable
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QLineEdit,
    QHBoxLayout, QVBoxLayout, QFileDialog, QMessageBox, QProgressBar, QSpinBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

import imagej  # pyimagej


# ---------------- ImageJ macro (Macro final (by Hyunho) ----------------
_IJM = r"""
#@ String inPath
#@ String outPath
#@ Integer rolling
#@ Integer thr1
#@ Integer thr2
#@ Integer maxval

open(inPath);
img1 = getTitle();

run("Duplicate...", " ");
img2 = getTitle();

selectWindow(img2);
run("Subtract Background...", "rolling=" + rolling);
setThreshold(thr1, maxval);
run("Convert to Mask");
run("Invert");

imageCalculator("Subtract create", img1, img2);

setThreshold(thr2, maxval);
run("Convert to Mask");
run("Invert");

saveAs("Tiff", outPath);
run("Close All");
"""


# ---------------- 배치 실행 워커 (UI 멈춤 방지) ----------------
class BatchWorker(QThread):
    """
    - BatchWorker class for running batch image processing in the background.
    - Prevents the main GUI thread from freezing while ImageJ macros are executed.
    - Emits signals to update the GUI: progress, finished, and error states.
    """
    progressed = pyqtSignal(int, int, str)   # (current, total, saved_path)
    finished_ok = pyqtSignal(int, str)       # (count, outdir)
    failed = pyqtSignal(str)

    def __init__(self, input_dir: str, patterns: Iterable[str],
                 rolling: int, thr1: int, thr2: int, maxval: int, parent=None):
        super().__init__(parent)
        self.input_dir = input_dir
        self.patterns = list(patterns)
        self.rolling = int(rolling)
        self.thr1 = int(thr1)
        self.thr2 = int(thr2)
        self.maxval = int(maxval)

    def run(self):
        try:
            # Fiji(headless) init
            ij = imagej.init()

            files = []
            for pat in self.patterns:
                files.extend(glob.glob(os.path.join(self.input_dir, pat)))
            files.sort()
            if not files:
                self.failed.emit("No target images in selected folder")
                return

            outdir = os.path.join(self.input_dir, "imgj_proc")
            os.makedirs(outdir, exist_ok=True)

            total = len(files)
            count = 0
            for fp in files:
                name, _ = os.path.splitext(os.path.basename(fp))
                out_path = os.path.join(outdir, f"{name}.tif")

                args = {
                    "inPath": fp,
                    "outPath": out_path,
                    "rolling": self.rolling,
                    "thr1": self.thr1,
                    "thr2": self.thr2,
                    "maxval": self.maxval,
                }

                # run imagej macro with selected arguments
                ij.py.run_macro(_IJM, args)
                count += 1
                self.progressed.emit(count, total, out_path)

            self.finished_ok.emit(count, outdir)

        except Exception as e:
            self.failed.emit(str(e))


# --- GUI
class ImageJBatchGUI(QWidget):
    """
    - Main GUI widget for user interaction.
    - Provides controls to select input folder, set processing parameters, and start batch processing.
    - Launches BatchWorker thread when "Run Batch" is clicked.
    - Updates progress bar and status labels based on worker signals, and shows dialogs on completion or error.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("[Image Processing] ImageJ Macro Batch")
        self.setGeometry(200, 200, 600, 220)

        # 폴더 표시/선택
        self.dir_label = QLabel("Input Folder: (not selected)")
        self.btn_select = QPushButton("Select Folder")
        self.btn_select.clicked.connect(self.select_folder)

        # 파라미터: rolling / thr1 / thr2 / maxval
        self.rolling = QSpinBox()
        self.rolling.setRange(1, 100000)
        self.rolling.setValue(10)

        self.thr1 = QSpinBox()
        self.thr1.setRange(0, 65535)
        self.thr1.setValue(11)

        self.thr2 = QSpinBox()
        self.thr2.setRange(0, 65535)
        self.thr2.setValue(13285)

        self.maxval = QSpinBox()
        self.maxval.setRange(1, 65535)
        self.maxval.setValue(65535)  # 16-bit 기준 / 8-bit면 255로 변경

        # 실행 버튼 / 진행 표시
        self.btn_run = QPushButton("Run Batch")
        self.btn_run.clicked.connect(self.run_batch)
        self.progress = QProgressBar()
        self.status = QLabel("Ready")

        # 레이아웃
        row1 = QHBoxLayout()
        row1.addWidget(self.dir_label)
        row1.addWidget(self.btn_select)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("rolling"))
        row2.addWidget(self.rolling)
        row2.addSpacing(10)
        row2.addWidget(QLabel("thr1"))
        row2.addWidget(self.thr1)
        row2.addSpacing(10)
        row2.addWidget(QLabel("thr2"))
        row2.addWidget(self.thr2)
        row2.addSpacing(10)
        row2.addWidget(QLabel("maxval"))
        row2.addWidget(self.maxval)

        row3 = QHBoxLayout()
        row3.addWidget(self.btn_run)
        row3.addWidget(self.progress)

        main = QVBoxLayout()
        main.addLayout(row1)
        main.addLayout(row2)
        main.addLayout(row3)
        main.addWidget(self.status)
        self.setLayout(main)

        self.input_dir = None
        self.worker = None

    def select_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if d:
            self.input_dir = d
            self.dir_label.setText(f"Input Folder: {d}")

    def run_batch(self):
        if not self.input_dir:
            QMessageBox.information(self, "Info", "먼저 입력 폴더를 선택하세요.")
            return

        # 8-bit 이미지만이면 maxval=255로 설정하길 권장
        pat = ("*.tif", "*.tiff", "*.png", "*.jpg", "*.jpeg")
        self.worker = BatchWorker(
            input_dir=self.input_dir,
            patterns=pat,
            rolling=self.rolling.value(),
            thr1=self.thr1.value(),
            thr2=self.thr2.value(),
            maxval=self.maxval.value(),
        )
        self.worker.progressed.connect(self.on_progress)
        self.worker.finished_ok.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)

        self.progress.setValue(0)
        self.status.setText("Processing...")
        self.btn_run.setEnabled(False)
        self.worker.start()

    def on_progress(self, cur, total, saved_path):
        self.progress.setMaximum(total)
        self.progress.setValue(cur)
        self.status.setText(f"[{cur}/{total}] Saved: {os.path.basename(saved_path)}")

    def on_finished(self, count, outdir):
        self.status.setText(f"Done. {count} file(s) → {outdir}")
        self.btn_run.setEnabled(True)
        QMessageBox.information(self, "Done", f"Processed {count} file(s).\nSaved to:\n{outdir}")

    def on_failed(self, msg):
        self.status.setText(f"Failed: {msg}")
        self.btn_run.setEnabled(True)
        QMessageBox.critical(self, "Error", msg)


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = ImageJBatchGUI()
    w.show()
    sys.exit(app.exec_())
