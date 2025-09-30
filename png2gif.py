# p5_png2anim.py
# -*- coding: utf-8 -*-
"""
PNG 시퀀스를 숫자(0,1,2,...) 순으로 읽어
- GIF (무한 반복)
- MP4 (H.264/MP4 컨테이너)
로 내보내는 간단 GUI.

필요 패키지:
  pip install pillow opencv-python PyQt5
"""

import os
import re
import glob
from typing import List, Tuple

import numpy as np
from PIL import Image
import cv2

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog,
    QHBoxLayout, QVBoxLayout, QMessageBox, QComboBox, QCheckBox
)
from PyQt5.QtCore import Qt

# ----- 숫자 자연 정렬용 -----
_num_re = re.compile(r'(\d+)')
def natural_key(s: str):
    return [int(t) if t.isdigit() else t.lower() for t in _num_re.split(s)]

def list_pngs_numeric(input_dir: str) -> List[str]:
    files = glob.glob(os.path.join(input_dir, "*.png"))
    files.sort(key=lambda p: natural_key(os.path.basename(p)))
    return files

def ensure_same_size(images: List[Image.Image]) -> Tuple[List[Image.Image], Tuple[int, int]]:
    """
    PIL Image 리스트를 첫 프레임 크기에 맞춰 모두 리사이즈 (안전)
    """
    if not images:
        raise RuntimeError("이미지가 없습니다.")
    w, h = images[0].size
    fixed = [im if im.size == (w, h) else im.resize((w, h), Image.BILINEAR) for im in images]
    return fixed, (w, h)

def save_gif(png_paths: List[str], out_path: str, fps: int):
    """
    PNG → GIF 저장
    fps → frame duration(ms) = 1000 / fps
    """
    duration = max(1, int(1000 / fps))
    frames = [Image.open(p) for p in png_paths]
    frames, _ = ensure_same_size(frames)
    frames[0].save(
        out_path,
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=0  # 무한 반복
    )

def save_mp4(png_paths: List[str], out_path: str, fps: int):
    """
    PNG → MP4 저장 (코덱: mp4v)
    """
    frames = [Image.open(p).convert("RGB") for p in png_paths]
    frames, (w, h) = ensure_same_size(frames)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    vw = cv2.VideoWriter(out_path, fourcc, fps, (w, h))
    if not vw.isOpened():
        raise RuntimeError("VideoWriter initailize failed")

    for im in frames:
        bgr = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
        vw.write(bgr)
    vw.release()




class PNG2AnimGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PNG → GIF / MP4")
        self.setGeometry(300, 300, 540, 180)

        self.input_dir = None

        # 위젯
        self.dir_label = QLabel("Input: (not selected)")
        self.btn_select = QPushButton("Select Folder")
        self.btn_select.clicked.connect(self.select_folder)

        self.fps_label = QLabel("Frame Rate:")
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["1","2", "3","4","5", "10", "15","20", "30"])
        self.fps_combo.setCurrentText("15")

        self.chk_gif = QCheckBox("Export GIF")
        self.chk_mp4 = QCheckBox("Export MP4")
        self.chk_gif.setChecked(True)
        self.chk_mp4.setChecked(True)

        self.btn_run = QPushButton("Make Animation")
        self.btn_run.clicked.connect(self.run_make)

        # 레이아웃
        row1 = QHBoxLayout()
        row1.addWidget(self.dir_label)
        row1.addWidget(self.btn_select)

        row2 = QHBoxLayout()
        row2.addWidget(self.fps_label)
        row2.addWidget(self.fps_combo)
        row2.addSpacing(20)
        row2.addWidget(self.chk_gif)
        row2.addWidget(self.chk_mp4)
        row2.addStretch()

        row3 = QHBoxLayout()
        row3.addStretch()
        row3.addWidget(self.btn_run)

        main = QVBoxLayout()
        main.addLayout(row1)
        main.addLayout(row2)
        main.addLayout(row3)
        self.setLayout(main)

    def select_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select PNG Folder")
        if d:
            self.input_dir = d
            self.dir_label.setText(f"Input: {d}")

    def run_make(self):
        if not self.input_dir:
            QMessageBox.information(self, "Info", "먼저 PIV results 폴더를 선택하세요.")
            return

        try:
            files = list_pngs_numeric(self.input_dir)
            if not files:
                raise RuntimeError("선택한 폴더에 PNG가 없습니다.")

            fps = int(self.fps_combo.currentText())

            out_dir = os.path.join(self.input_dir, "anim_exports")
            os.makedirs(out_dir, exist_ok=True)

            done_paths = []

            if self.chk_gif.isChecked():
                gif_path = os.path.join(out_dir, f"animation_{fps}fps.gif")
                save_gif(files, gif_path, fps=fps)
                done_paths.append(gif_path)

            if self.chk_mp4.isChecked():
                mp4_path = os.path.join(out_dir, f"animation_{fps}fps.mp4")
                save_mp4(files, mp4_path, fps=fps)
                done_paths.append(mp4_path)

            if not done_paths:
                QMessageBox.information(self, "Info", "내보낼 포맷을 선택하세요 (GIF/MP4).")
                return

            msg = "저장 완료:\n" + "\n".join(done_paths)
            QMessageBox.information(self, "Done", msg)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"{e}")


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = PNG2AnimGUI()
    w.show()
    sys.exit(app.exec_())
