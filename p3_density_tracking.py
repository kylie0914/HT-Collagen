# p3_density_tracking.py
# -*- coding: utf-8 -*-
"""
Density Tracking GUI (AF/DF tabs) with robust input handling.

- Any input mix (16-bit/8-bit .tif/.tiff, 8-bit .png/.jpg) is converted to 8-bit PNG
  into a working folder "density_input_8bit" (sibling dir of selected folder).
- All processing (Area Fraction, Diff) runs ONLY on those 8-bit PNGs to ensure consistency.
- UI organized into tabs:
    1) Area Fraction (AF)
    2) Diff Result (DF)

Extras in this build:
- Current Directory label in bold.
- All canvases/toolbars are centered in their layouts.
- AF tab: Heatmap & Overlay axes zoom/pan are synchronized both ways.
- AF tab: Save = full heatmap with grid + per-cell means + RED rectangle for current zoomed view.
"""

import sys, os, re, warnings, ctypes, csv  # ← csv 추가
import numpy as np
import cv2

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib import patheffects as pe
import matplotlib.patches as patches

warnings.filterwarnings('ignore')

# High-DPI (Windows)
try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

# ---------- Helpers ----------
_num_re = re.compile(r'(\d+)')
def natural_key(s: str):
    """Natural sort: treat numbers as numbers (e.g. im_2 < im_10)."""
    return [int(t) if t.isdigit() else t.lower() for t in _num_re.split(s)]

def convert_all_to_8bit_png(src_dir, dst_name="density_input_8bit"):
    """
    Convert all images in `src_dir` (tif/tiff/png/jpg/jpeg) to 8-bit grayscale PNG.
    Saves to sibling folder: <src_dir>/../<dst_name>/<basename>_8bit.png
    Returns (dst_dir, out_files).
    """
    dst_dir = os.path.join(src_dir, "../", dst_name)
    os.makedirs(dst_dir, exist_ok=True)
    exts = (".tif", ".tiff", ".png", ".jpg", ".jpeg")
    files = [f for f in os.listdir(src_dir) if f.lower().endswith(exts)]
    files.sort(key=natural_key)

    out_files = []
    for f in files:
        src_path = os.path.join(src_dir, f)
        img = cv2.imread(src_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            continue
        if img.ndim == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if img.dtype == np.uint16:
            mn, mx = float(img.min()), float(img.max())
            if mx > mn:
                img8 = ((img - mn) / (mx - mn) * 255.0).astype(np.uint8)
            else:
                img8 = np.zeros_like(img, dtype=np.uint8)
        else:
            img8 = img.astype(np.uint8)

        base = os.path.splitext(f)[0]
        out_name = f"{base}.png"
        out_path = os.path.join(dst_dir, out_name)
        cv2.imwrite(out_path, img8)
        out_files.append(out_name)

    return dst_dir, out_files


# ---------- Area Fraction Tab ----------
class densityEstimation(QWidget):
    """
    Area Fraction tab widget
    - Folder selection → convert all inputs to 8-bit PNG (sibling 'density_input_8bit') → list PNGs
    - Heatmap & Overlay zoom/pan synchronized in both directions.
    - Save = Full heatmap with grid+per-cell means + RED rectangle for current zoomed region.
    """
    def __init__(self):
        super().__init__()
        self.process_dir = None
        self.grid_scale = 25       # grid cell pixels on the 1000x1000 analysis canvas
        self.save_directory = "./"
        self.selected_file = None
        self.heatmap_density_data = None
        self._last_heatmap_size = None

        # sync/preview state
        self._last_bi_img_resize = None       # (1000x1000) raw 8-bit for overlay
        self._last_heatmap_resized = None     # (1000x1000) heatmap float
        self._sync_lock = False               # avoid recursive callbacks
        self._cids = {}                       # mpl callback ids
        self._last_roi_stats = None           # ← ROI 통계 보관

        self.init_ui()

    # ---- UI ----
    def init_ui(self):
        # Top labels
        self.current_dir_label = QLabel("Current Directory: Not selected", self)
        self.save_dir_label = QLabel("Save Directory: Not selected", self)

        # Matplot canvases + labels (Raw / Heatmap / Overlay)
        self.raw_fig = Figure(figsize=(5, 5))
        self.raw_image_canvas = FigureCanvas(self.raw_fig)
        self.raw_toolbar = NavigationToolbar(self.raw_image_canvas, self)
        self.raw_ax = None
        self.raw_image_label = QLabel(self); self.raw_image_label.setText(" Raw Image (8-bit PNG) "); self.raw_image_label.setFont(QFont('Arial', 12))

        self.heatmap_fig = Figure(figsize=(5, 5))
        self.heatmap_canvas = FigureCanvas(self.heatmap_fig)
        self.heatmap_toolbar = NavigationToolbar(self.heatmap_canvas, self)
        self.heatmap_ax = None
        self.heatmap_image_label = QLabel(self); self.heatmap_image_label.setText(" Heatmap Image "); self.heatmap_image_label.setFont(QFont('Arial', 12))

        self.overlay_fig = Figure(figsize=(5, 5))
        self.overlay_canvas = FigureCanvas(self.overlay_fig)
        self.overlay_toolbar = NavigationToolbar(self.overlay_canvas, self)
        self.overlay_ax = None
        self.overlay_image_label = QLabel(self); self.overlay_image_label.setText(" Overlay (Raw + Heatmap) "); self.overlay_image_label.setFont(QFont('Arial', 12))

        # Stats
        self.density_text = QLabel(self); self.density_text.setText(" [Measurement]  "); self.density_text.setFont(QFont('Arial', 18))
        self.density_min_text = QLabel(self); self.density_min_text.setText(" [min] "); self.density_min_text.setFont(QFont('Arial', 12))
        self.density_max_text = QLabel(self); self.density_max_text.setText(" [max] "); self.density_max_text.setFont(QFont('Arial', 12))
        self.density_mean_text = QLabel(self); self.density_mean_text.setText(" [mean] "); self.density_mean_text.setFont(QFont('Arial', 12))
        self.density_std_text = QLabel(self); self.density_std_text.setText(" [std] "); self.density_std_text.setFont(QFont('Arial', 12))

        # Buttons / file list
        self.select_dir_button = QPushButton("Select Directory", self)
        self.save_button = QPushButton("Save Results", self)
        self.file_list = QListWidget(self)

        # ---- Layout (Area tab only) ----
        self.setLayout(self.UI_layout_area())

        # Signals
        self.select_dir_button.clicked.connect(self.select_directory)
        self.file_list.itemClicked.connect(self.display_image)
        self.save_button.clicked.connect(self.save_results)

    def UI_layout_area(self):
        # top
        top_left_layout = QVBoxLayout()
        top_left_layout.addWidget(self.current_dir_label)
        top_left_layout.addWidget(self.save_dir_label)
        top_layout = QHBoxLayout()
        top_layout.addLayout(top_left_layout)

        # middle (raw + heatmap)
        raw_img_layout = QVBoxLayout()
        raw_img_layout.addWidget(self.raw_image_label, 0, Qt.AlignHCenter)
        raw_img_layout.addWidget(self.raw_image_canvas, 0, Qt.AlignCenter)
        raw_img_layout.addWidget(self.raw_toolbar, 0, Qt.AlignHCenter)

        heatmap_layout = QVBoxLayout()
        heatmap_layout.addWidget(self.heatmap_image_label, 0, Qt.AlignHCenter)
        heatmap_layout.addWidget(self.heatmap_canvas, 0, Qt.AlignCenter)
        heatmap_layout.addWidget(self.heatmap_toolbar, 0, Qt.AlignHCenter)

        middle_layout1 = QHBoxLayout()
        middle_layout1.setSpacing(20)
        middle_layout1.addLayout(raw_img_layout)
        middle_layout1.addLayout(heatmap_layout)

        # bottom (overlay + stats + list)
        overlay_layout = QVBoxLayout()
        overlay_layout.addWidget(self.overlay_image_label, 0, Qt.AlignHCenter)
        overlay_layout.addWidget(self.overlay_canvas, 0, Qt.AlignCenter)
        overlay_layout.addWidget(self.overlay_toolbar, 0, Qt.AlignHCenter)

        control_layout = QVBoxLayout()
        control_layout.setSpacing(20)
        control_layout.addWidget(self.density_text)
        control_layout.addWidget(self.density_min_text)
        control_layout.addWidget(self.density_max_text)
        control_layout.addWidget(self.density_mean_text)
        control_layout.addWidget(self.density_std_text)
        control_layout.addStretch()
        control_layout.addWidget(self.save_button)

        filelist_layout = QVBoxLayout()
        filelist_layout.setContentsMargins(0, 30, 0, 0)
        filelist_layout.addWidget(self.file_list)
        filelist_layout.addWidget(self.select_dir_button)

        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)
        bottom_layout.addLayout(overlay_layout, stretch=4)
        bottom_layout.addLayout(control_layout, stretch=3)
        bottom_layout.addLayout(filelist_layout, stretch=2)

        area_layout = QVBoxLayout()
        area_layout.addLayout(top_layout)
        area_layout.addLayout(middle_layout1)
        area_layout.addLayout(bottom_layout)
        return area_layout

    # ---- UI helpers ----
    def _set_current_dir_text(self, directory: str, process_dir: str = None):
        """Make 'Current Directory:' bold using HTML RichText."""
        self.current_dir_label.setTextFormat(Qt.RichText)
        html = f"<b>Current Directory:</b> {directory}"
        if process_dir:
            html += f"<br>(Use: {process_dir})"
        self.current_dir_label.setText(html)

    # ---- Core funcs (AF) ----
    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if not directory:
            return

        # convert all inputs to 8-bit PNG working folder (sibling dir)
        self.process_dir, _ = convert_all_to_8bit_png(directory)
        self._set_current_dir_text(directory, self.process_dir)

        # save dir (sibling AFmode)
        self.save_directory = os.path.join(directory, "../","density_results", "AFmode")
        os.makedirs(self.save_directory, exist_ok=True)
        self.save_dir_label.setText(f"Save Directory: {self.save_directory}")

        self.list_png_files(self.process_dir)

    def list_png_files(self, directory):
        self.file_list.clear()
        files = [f for f in os.listdir(directory) if f.lower().endswith(".png")]
        files.sort(key=natural_key)
        for f in files:
            self.file_list.addItem(f)

    def matplotFig_init(self):
        self.raw_fig.clf()
        self.heatmap_fig.clf()
        self.overlay_fig.clf()

        self.raw_ax = self.raw_fig.subplots()
        self.raw_ax.set_axis_off()
        self.heatmap_ax = self.heatmap_fig.subplots()
        self.heatmap_ax.set_axis_off()
        self.overlay_ax = self.overlay_fig.subplots()
        self.overlay_ax.set_axis_off()

    def draw_rawImg(self, bi_img_display):
        self.raw_ax.cla()
        img = self.raw_ax.imshow(bi_img_display, cmap="gray")
        self.raw_ax.set_aspect('equal', adjustable='box')
        self.raw_ax.set_anchor('C')
        divider = make_axes_locatable(self.raw_ax)
        cax = divider.append_axes("right", size="5%", pad=0.05)
        self.raw_fig.colorbar(img, ax=self.raw_ax, orientation='vertical', cax=cax)
        self.raw_ax.set_axis_off()
        self.raw_fig.tight_layout()
        self.raw_image_canvas.draw()

    def draw_heatmap(self, heatmap_density_mat_resized):
        self.heatmap_ax.cla()
        img = self.heatmap_ax.imshow(heatmap_density_mat_resized, interpolation='bilinear')
        self.heatmap_ax.set_aspect('equal', adjustable='box')
        self.heatmap_ax.set_anchor('C')
        divider = make_axes_locatable(self.heatmap_ax)
        cax = divider.append_axes("right", size="5%", pad=0.05)
        self.heatmap_fig.colorbar(img, ax=self.heatmap_ax, orientation='vertical', cax=cax)
        self.heatmap_ax.set_axis_off()
        self.heatmap_fig.tight_layout()
        self.heatmap_canvas.draw()

    def draw_overlay(self, bi_img_resize, heatmap_density_mat_resized):
        self.overlay_ax.cla()
        self.overlay_ax.imshow(bi_img_resize, cmap='gray', alpha=1.0)
        self.overlay_ax.imshow(heatmap_density_mat_resized, interpolation='bilinear', alpha=0.6)
        self.overlay_ax.set_aspect('equal', adjustable='box')
        self.overlay_ax.set_anchor('C')
        self.overlay_ax.set_axis_off()
        self.overlay_fig.tight_layout()
        self.overlay_canvas.draw()

    def calc_heatmap(self, binary_image, bi_img_resize):
        """Compute per-grid density from a binary image (1=foreground)."""
        hematmap_ratio = []
        heatmap_density = []
        for y in range(0, bi_img_resize.shape[0], self.grid_scale):
            for x in range(0, bi_img_resize.shape[1], self.grid_scale):
                grid = binary_image[y:y + self.grid_scale, x:x + self.grid_scale]
                one_ratio = np.count_nonzero(grid) / (self.grid_scale ** 2)
                # empirical calibration
                one_density = float((one_ratio - 0.1142) / 0.069721)
                hematmap_ratio.append(one_ratio)
                heatmap_density.append(one_density)
        return hematmap_ratio, heatmap_density

    # ===== 추가: 현재 뷰(ROI) → 통계 계산 =====
    def _get_current_view_rect(self):
        """
        Heatmap axes의 현재 뷰(줌/팬) 영역을 1000x1000 좌표계로 반환.
        (x0, x1, y0, y1)
        """
        if self.heatmap_ax is None:
            return (0.0, 1000.0, 0.0, 1000.0)
        hxmin, hxmax = self.heatmap_ax.get_xlim()
        hymin, hymax = self.heatmap_ax.get_ylim()
        x0, x1 = (min(hxmin, hxmax), max(hxmin, hxmax))
        y0, y1 = (min(hymin, hymax), max(hymin, hymax))
        x0 = max(0.0, min(1000.0, x0)); x1 = max(0.0, min(1000.0, x1))
        y0 = max(0.0, min(1000.0, y0)); y1 = max(0.0, min(1000.0, y1))
        return (x0, x1, y0, y1)

    def _update_measurements_from_view(self):
        """
        현재 보이는 영역(heatmap axes)의 ROI에 대해 min/max/mean/std 계산 → 라벨 갱신.
        """
        if self._last_heatmap_resized is None:
            return

        x0, x1, y0, y1 = self._get_current_view_rect()
        ix0, ix1 = int(np.floor(x0)), int(np.ceil(x1))
        iy0, iy1 = int(np.floor(y0)), int(np.ceil(y1))
        roi = self._last_heatmap_resized[iy0:iy1, ix0:ix1]
        if roi.size == 0:
            return

        vmin = float(np.min(roi))
        vmax = float(np.max(roi))
        vmean = float(np.mean(roi))
        vstd = float(np.std(roi))

        self.density_min_text.setText(" [min] :  {0}".format(np.round(vmin, 5)))
        self.density_max_text.setText(" [max] :  {0}".format(np.round(vmax, 5)))
        self.density_mean_text.setText(" [mean] :  {0}".format(np.round(vmean, 5)))
        self.density_std_text.setText(" [std] :  {0}".format(np.round(vstd, 5)))

        self._last_roi_stats = {
            "x0": x0, "x1": x1, "y0": y0, "y1": y1,
            "min": vmin, "max": vmax, "mean": vmean, "std": vstd
        }

    def _attach_zoom_sync(self):
        """Synchronize heatmap & overlay axes (zoom/pan both ways) + ROI 통계 갱신."""
        if self.heatmap_ax is None or self.overlay_ax is None:
            return

        def sync_from_heatmap(ax):
            if self._sync_lock: return
            self._sync_lock = True
            try:
                self.overlay_ax.set_xlim(self.heatmap_ax.get_xlim())
                self.overlay_ax.set_ylim(self.heatmap_ax.get_ylim())
                self.overlay_canvas.draw_idle()
            finally:
                self._sync_lock = False
            self._update_measurements_from_view()

        def sync_from_overlay(ax):
            if self._sync_lock: return
            self._sync_lock = True
            try:
                self.heatmap_ax.set_xlim(self.overlay_ax.get_xlim())
                self.heatmap_ax.set_ylim(self.overlay_ax.get_ylim())
                self.heatmap_canvas.draw_idle()
            finally:
                self._sync_lock = False
            self._update_measurements_from_view()

        # disconnect previous
        for key, cid in list(self._cids.items()):
            try:
                if key in ('hx', 'hy'):
                    self.heatmap_ax.callbacks.disconnect(cid)
                else:
                    self.overlay_ax.callbacks.disconnect(cid)
            except Exception:
                pass
            self._cids.pop(key, None)

        # connect
        self._cids['hx'] = self.heatmap_ax.callbacks.connect('xlim_changed', sync_from_heatmap)
        self._cids['hy'] = self.heatmap_ax.callbacks.connect('ylim_changed', sync_from_heatmap)
        self._cids['ox'] = self.overlay_ax.callbacks.connect('xlim_changed', sync_from_overlay)
        self._cids['oy'] = self.overlay_ax.callbacks.connect('ylim_changed', sync_from_overlay)

        # 연결 직후 한 번 계산(초기 표시 보정)
        self._update_measurements_from_view()

    def display_image(self):
        if not self.process_dir:
            return
        item = self.file_list.currentItem()
        if not item:
            return

        # init figs
        self.matplotFig_init()

        self.selected_file = item.text()
        img_path = os.path.join(self.process_dir, self.selected_file)

        # Load 8-bit PNG
        binary_image = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if binary_image is None:
            return
        binary_image = 255 - binary_image  # foreground bright
        bi_img_resize = cv2.resize(binary_image, (1000, 1000))   # analysis canvas
        bi_img_display = cv2.resize(bi_img_resize, (400, 400))   # preview
        heatmap_size = int(bi_img_resize.shape[0] / self.grid_scale)
        self._last_heatmap_size = heatmap_size

        # draw raw
        self.draw_rawImg(bi_img_display)

        # densities
        _, heatmap_density = self.calc_heatmap(binary_image, bi_img_resize)
        self.heatmap_density_data = heatmap_density

        # (초기 표시는 전체 영역 기준이었지만, 이제는 ROI 갱신 함수가 최종 반영)
        self.density_min_text.setText(" [min] :  {0}".format(np.round(np.min(heatmap_density), 5)))
        self.density_max_text.setText(" [max] :  {0}".format(np.round(np.max(heatmap_density), 5)))
        self.density_mean_text.setText(" [mean] :  {0}".format(np.round(np.mean(heatmap_density), 5)))
        self.density_std_text.setText(" [std] :  {0}".format(np.round(np.std(heatmap_density), 5)))

        heatmap_density_mat = np.array(heatmap_density).reshape(heatmap_size, heatmap_size)
        heatmap_density_mat_resized = cv2.resize(heatmap_density_mat, (bi_img_resize.shape[1], bi_img_resize.shape[0]),
                                                 interpolation=cv2.INTER_LINEAR)#  bilinear #cv2.INTER_NEAREST)

        # draw heatmap + overlay
        self.draw_heatmap(heatmap_density_mat_resized)
        self.draw_overlay(bi_img_resize, heatmap_density_mat_resized)

        # remember current 1000x1000 arrays (for save & rectangle)
        self._last_bi_img_resize = bi_img_resize.copy()
        self._last_heatmap_resized = heatmap_density_mat_resized.copy()

        # sync zoom both ways
        self._attach_zoom_sync()

        # ★ 현재 뷰 기준 통계로 라벨 갱신 (처음에는 전체 영역)
        self._update_measurements_from_view()

    def save_results(self):
        """
        Save a FULL heatmap image (1000x1000) with:
          - Grid lines and per-cell mean numbers
          - RED rectangle indicating the current zoomed view on heatmap
        """
        if self.heatmap_density_data is None or self.selected_file is None:
            QMessageBox.information(self, "Info", "No heatmap to save. Select a file first.")
            return

        base = os.path.splitext(self.selected_file)[0]
        heatmap_size = self._last_heatmap_size or int(1000 / self.grid_scale)
        cell = self.grid_scale

        # Full heatmap matrix (heatmap_size x heatmap_size)
        H = np.array(self.heatmap_density_data).reshape(heatmap_size, heatmap_size)
        # Upsample to 1000x1000 (nearest) to align with grid
        H_resized = cv2.resize(H, (1000, 1000), interpolation=cv2.INTER_NEAREST)

        # Current view from heatmap axes (zoomed area)
        hxmin, hxmax = self.heatmap_ax.get_xlim()
        hymin, hymax = self.heatmap_ax.get_ylim()
        x0, x1 = min(hxmin, hxmax), max(hxmin, hxmax)
        y0, y1 = min(hymin, hymax), max(hymin, hymax)

        # Build full figure
        dpi = 150
        figA, axA = plt.subplots(figsize=(8, 8), dpi=dpi)
        imA = axA.imshow(H_resized, interpolation='bilinear', origin='upper', cmap='viridis')
        axA.set_aspect('equal', adjustable='box')
        axA.set_anchor('C')

        for k in range(heatmap_size + 1):
            pos = k * cell
            axA.axvline(pos, color='w', linewidth=0.6)
            axA.axhline(pos, color='w', linewidth=0.6)

        for i in range(heatmap_size):
            for j in range(heatmap_size):
                cx = (j + 0.5) * cell
                cy = (i + 0.5) * cell
                axA.text(cx, cy, f"{H[i, j]:.1f}",
                         ha="center", va="center", color="white", fontsize=4,
                         path_effects=[pe.withStroke(linewidth=1.2, foreground="black")])

        # Red rectangle for current zoomed view
        rect = patches.Rectangle((x0, y0), x1 - x0, y1 - y0,
                                 fill=False, edgecolor='red', linewidth=2.0, linestyle='--')
        axA.add_patch(rect)

        # Show whole canvas
        axA.set_xlim(0, 1000)
        axA.set_ylim(1000, 0)
        axA.set_axis_off()
        figA.colorbar(imA, ax=axA, fraction=0.046, pad=0.04)

        # 3-sec preview then save
        plt.show(block=False); plt.pause(1.5)
        outA = os.path.join(self.save_directory, f"heatmap_grid_FULL_{base}.png")
        figA.savefig(outA, bbox_inches='tight', dpi=dpi)
        plt.close(figA)

        # ----- CSV 저장 (현재 뷰 기준 통계) -----
        if not hasattr(self, "_last_roi_stats") or self._last_roi_stats is None:
            self._update_measurements_from_view()

        base_csv = os.path.splitext(self.selected_file)[0] + ".csv"
        out_csv = os.path.join(self.save_directory, base_csv)
        x0v = self._last_roi_stats.get("x0", 0.0)
        x1v = self._last_roi_stats.get("x1", 1000.0)
        y0v = self._last_roi_stats.get("y0", 0.0)
        y1v = self._last_roi_stats.get("y1", 1000.0)
        vmin = self._last_roi_stats.get("min", float('nan'))
        vmax = self._last_roi_stats.get("max", float('nan'))
        vmean = self._last_roi_stats.get("mean", float('nan'))
        vstd = self._last_roi_stats.get("std", float('nan'))

        try:
            os.makedirs(self.save_directory, exist_ok=True)
            with open(out_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["file","x0","x1","y0","y1","min","max","mean","std"])
                writer.writerow([
                    self.selected_file,
                    np.round(x0v, 2), np.round(x1v, 2),
                    np.round(y0v, 2), np.round(y1v, 2),
                    np.round(vmin, 6), np.round(vmax, 6),
                    np.round(vmean, 6), np.round(vstd, 6)
                ])
        except Exception as e:
            print(f"[save_results][CSV] error: {e}")

        # QMessageBox.information(self, "Saved", f"Saved:\n{outA}\n{out_csv}")


# ---------- Diff Result Tab (embedded) ----------
class densityTracking(QWidget):
    """
    Diff Result tab widget.
    - Folder selection → convert all inputs to 8-bit PNG (sibling 'density_input_8bit') → select two PNGs
    - Compute and display Heatmap Difference (image2 - image1) on 1000x1000 canvas
    """
    def __init__(self):
        super().__init__()
        self.process_dir = None
        self.selected_file_1 = None
        self.selected_file_2 = None
        self.grid_scale = 25
        self.heatmap_density_data1 = None
        self.heatmap_density_data2 = None
        self.directory = None
        self.save_directory = "./"

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("[CSB-MGH] Diff Result")
        self.setGeometry(550, 150, 900, 1000)

        # components
        self.current_dir_label = QLabel("Current Directory: Not selected", self)
        self.save_dir_label = QLabel("Save Directory: Not selected", self)

        # raw canvases 1/2
        self.raw_fig_1 = Figure(figsize=(4,4))
        self.raw_canvas_1 = FigureCanvas(self.raw_fig_1)
        self.raw_toolbar_1 = NavigationToolbar(self.raw_canvas_1, self)
        self.raw_ax_1 = None

        self.raw_fig_2 = Figure(figsize=(4,4))
        self.raw_canvas_2 = FigureCanvas(self.raw_fig_2)
        self.raw_toolbar_2 = NavigationToolbar(self.raw_canvas_2, self)
        self.raw_ax_2 = None

        # heatmap canvases 1/2
        self.heatmap_fig_1 = Figure(figsize=(4,4))
        self.heatmap_canvas_1 = FigureCanvas(self.heatmap_fig_1)
        self.heatmap_toolbar_1 = NavigationToolbar(self.heatmap_canvas_1, self)
        self.heatmap_ax_1 = None

        self.heatmap_fig_2 = Figure(figsize=(4,4))
        self.heatmap_canvas_2 = FigureCanvas(self.heatmap_fig_2)
        self.heatmap_toolbar_2 = NavigationToolbar(self.heatmap_canvas_2, self)
        self.heatmap_ax_2 = None

        # diff canvas
        self.diff_fig = Figure(figsize=(4,4))
        self.diff_canvas = FigureCanvas(self.diff_fig)
        self.diff_toolbar = NavigationToolbar(self.diff_canvas, self)
        self.diff_ax = None

        # labels
        self.raw_image_label_1 = QLabel(" Raw Image 1 (8-bit PNG)"); self.raw_image_label_1.setFont(QFont('Arial', 12))
        self.raw_image_label_2 = QLabel(" Raw Image 2 (8-bit PNG)"); self.raw_image_label_2.setFont(QFont('Arial', 12))
        self.heatmap_image_label_1 = QLabel(" Heatmap Image 1"); self.heatmap_image_label_1.setFont(QFont('Arial', 12))
        self.heatmap_image_label_2 = QLabel(" Heatmap Image 2"); self.heatmap_image_label_2.setFont(QFont('Arial', 12))
        self.diff_image_label = QLabel(" Diff Image: 2 - 1 "); self.diff_image_label.setFont(QFont('Arial', 12))

        # lists & buttons
        self.file_list_1 = QListWidget(self)
        self.file_list_2 = QListWidget(self)
        self.select_dir_file = QPushButton("Select Directory", self)
        self.calc_save_button = QPushButton("Calc. and Save", self)

        # layout
        self.setLayout(self.UI_layout_diff())

        # signals
        self.select_dir_file.clicked.connect(self.select_directory)
        self.file_list_1.itemClicked.connect(self.get_selectedFile_1)
        self.file_list_2.itemClicked.connect(self.get_selectedFile_2)
        self.calc_save_button.clicked.connect(self.calc_saveResult)

    def _set_current_dir_text(self, directory: str, process_dir: str = None):
        self.current_dir_label.setTextFormat(Qt.RichText)
        html = f"<b>Current Directory:</b> {directory}"
        if process_dir:
            html += f"<br>(Use: {process_dir})"
        self.current_dir_label.setText(html)

    def UI_layout_diff(self):
        top_layout = QVBoxLayout()
        top_layout.addWidget(self.current_dir_label)
        top_layout.addWidget(self.save_dir_label)

        raw_img1_layout = QVBoxLayout()
        raw_img1_layout.addWidget(self.raw_image_label_1, 0, Qt.AlignHCenter)
        raw_img1_layout.addWidget(self.raw_canvas_1, 0, Qt.AlignCenter)
        raw_img1_layout.addWidget(self.raw_toolbar_1, 0, Qt.AlignHCenter)

        raw_img2_layout = QVBoxLayout()
        raw_img2_layout.addWidget(self.raw_image_label_2, 0, Qt.AlignHCenter)
        raw_img2_layout.addWidget(self.raw_canvas_2, 0, Qt.AlignCenter)
        raw_img2_layout.addWidget(self.raw_toolbar_2, 0, Qt.AlignHCenter)

        diff_layout = QVBoxLayout()
        diff_layout.addWidget(self.diff_image_label, 0, Qt.AlignHCenter)
        diff_layout.addWidget(self.diff_canvas, 0, Qt.AlignCenter)
        diff_layout.addWidget(self.diff_toolbar, 0, Qt.AlignHCenter)

        middle_layout = QHBoxLayout()
        middle_layout.addLayout(raw_img1_layout)
        middle_layout.addLayout(raw_img2_layout)
        middle_layout.addLayout(diff_layout)

        heatmap_img1_layout = QVBoxLayout()
        heatmap_img1_layout.addWidget(self.heatmap_image_label_1, 0, Qt.AlignHCenter)
        heatmap_img1_layout.addWidget(self.heatmap_canvas_1, 0, Qt.AlignCenter)
        heatmap_img1_layout.addWidget(self.heatmap_toolbar_1, 0, Qt.AlignHCenter)

        heatmap_img2_layout = QVBoxLayout()
        heatmap_img2_layout.addWidget(self.heatmap_image_label_2, 0, Qt.AlignHCenter)
        heatmap_img2_layout.addWidget(self.heatmap_canvas_2, 0, Qt.AlignCenter)
        heatmap_img2_layout.addWidget(self.heatmap_toolbar_2, 0, Qt.AlignHCenter)

        filelist_layout = QHBoxLayout()
        filelist_layout.addWidget(self.file_list_1)
        filelist_layout.addWidget(self.file_list_2)

        file_save_layout = QVBoxLayout()
        file_save_layout.setContentsMargins(0,30,0,0)
        file_save_layout.addLayout(filelist_layout)
        file_save_layout.addWidget(self.select_dir_file)
        file_save_layout.addWidget(self.calc_save_button)

        bottom_layout = QHBoxLayout()
        bottom_layout.addLayout(heatmap_img1_layout, stretch=3)
        bottom_layout.addLayout(heatmap_img2_layout, stretch=3)
        bottom_layout.addLayout(file_save_layout, stretch=3)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addLayout(middle_layout)
        main_layout.addLayout(bottom_layout)
        return main_layout

    # ---- Core funcs (DF) ----
    def select_directory(self):
        self.directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if not self.directory:
            return

        self.process_dir, _ = convert_all_to_8bit_png(self.directory)
        self._set_current_dir_text(self.directory, self.process_dir)

        parent_dir = os.path.dirname(self.directory)  # drift_corr 의 상위 폴더
        self.save_directory = os.path.join(parent_dir, "density_results", "DFmode")
        os.makedirs(self.save_directory, exist_ok=True)

        self.save_dir_label.setText(f"Save Directory: {self.save_directory}")
        self.list_png_files(self.process_dir)

    def list_png_files(self, directory):
        self.file_list_1.clear()
        self.file_list_2.clear()
        files = [f for f in os.listdir(directory) if f.lower().endswith(".png")]
        files.sort(key=natural_key)
        for f in files:
            self.file_list_1.addItem(f)
            self.file_list_2.addItem(f)

    def _show_raw(self, canvas_fig, canvas_ax_attr_name, img8):
        fig = canvas_fig
        fig.clf()
        ax = fig.subplots()
        setattr(self, canvas_ax_attr_name, ax)
        im = ax.imshow(img8, cmap="gray")
        ax.set_aspect('equal', adjustable='box')
        ax.set_anchor('C')
        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="5%", pad=0.05)
        fig.colorbar(im, ax=ax, orientation='vertical', cax=cax)
        ax.set_axis_off()
        fig.tight_layout()
        canvas_fig.canvas.draw()

    def _show_heatmap_overlay(self, fig, ax_attr_name, img8_1000, heatmap_resized):
        fig.clf()
        ax = fig.subplots()
        setattr(self, ax_attr_name, ax)
        ax.imshow(img8_1000, cmap='gray', alpha=1.0)
        im = ax.imshow(heatmap_resized, interpolation='bilinear', alpha=0.6)
        ax.set_aspect('equal', adjustable='box')
        ax.set_anchor('C')
        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="5%", pad=0.05)
        fig.colorbar(im, ax=ax, orientation='vertical', cax=cax)
        ax.set_axis_off()
        fig.tight_layout()
        fig.canvas.draw()

    def _calc_heatmap(self, binary_image_1000):
        heatmap = []
        for y in range(0, binary_image_1000.shape[0], self.grid_scale):
            for x in range(0, binary_image_1000.shape[1], self.grid_scale):
                grid = binary_image_1000[y:y + self.grid_scale, x:x + self.grid_scale]
                one_ratio = np.count_nonzero(grid) / (self.grid_scale ** 2)
                one_density = float((one_ratio - 0.1142) / 0.069721)
                heatmap.append(one_density)
        size = int(binary_image_1000.shape[0] / self.grid_scale)
        heatmap_mat = np.array(heatmap).reshape(size, size)
        heatmap_resized = cv2.resize(heatmap_mat, (binary_image_1000.shape[1], binary_image_1000.shape[0]),
                                     interpolation=cv2.INTER_LINEAR)#NEAREST)
        return heatmap_resized

    def get_selectedFile_1(self):
        try:
            self.selected_file_1 = self.file_list_1.currentItem().text()
            img_path = os.path.join(self.process_dir, self.selected_file_1)
            img8 = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            img8_1000 = cv2.resize(img8, (1000, 1000))
            img8_1000 = 255 - img8_1000
            self._show_raw(self.raw_fig_1, 'raw_ax_1', img8_1000)
            heatmap1 = self._calc_heatmap(img8_1000)
            self._show_heatmap_overlay(self.heatmap_fig_1, 'heatmap_ax_1', img8_1000, heatmap1)
            self.heatmap_density_data1 = heatmap1
        except Exception as e:
            print(f"[get_selectedFile_1] error: {e}")

    def get_selectedFile_2(self):
        try:
            self.selected_file_2 = self.file_list_2.currentItem().text()
            img_path = os.path.join(self.process_dir, self.selected_file_2)
            img8 = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            img8_1000 = cv2.resize(img8, (1000, 1000))
            img8_1000 = 255 - img8_1000
            self._show_raw(self.raw_fig_2, 'raw_ax_2', img8_1000)
            heatmap2 = self._calc_heatmap(img8_1000)
            self._show_heatmap_overlay(self.heatmap_fig_2, 'heatmap_ax_2', img8_1000, heatmap2)
            self.heatmap_density_data2 = heatmap2
        except Exception as e:
            print(f"[get_selectedFile_2] error: {e}")

    def calc_saveResult(self):
        if self.heatmap_density_data1 is None or self.heatmap_density_data2 is None:
            print("Heatmap 1/2 not ready.")
            return
        try:
            heatmap_diff = self.heatmap_density_data2 - self.heatmap_density_data1
            self.diff_fig.clf()
            self.diff_ax = self.diff_fig.subplots()
            im = self.diff_ax.imshow(heatmap_diff, cmap='viridis', interpolation='bilinear')
            divider = make_axes_locatable(self.diff_ax)
            cax = divider.append_axes("right", size="5%", pad=0.05)
            self.diff_fig.colorbar(im, ax=self.diff_ax, orientation='vertical', cax=cax)
            self.diff_ax.set_axis_off()
            self.diff_fig.tight_layout()
            self.diff_canvas.draw()

            file_name = "{0}-{1}.{2}".format(
                os.path.splitext(self.selected_file_2)[0],
                os.path.splitext(self.selected_file_1)[0],
                os.path.splitext(self.selected_file_2)[1].lstrip('.')
            )
            out = os.path.normpath(os.path.join(self.save_directory, f"Diff_{file_name}"))
            print("out", out)
            os.makedirs(os.path.dirname(out), exist_ok=True)  # 부모 폴더 보장
            self.diff_fig.savefig(out, bbox_inches='tight', dpi=200)

        except Exception as e:
            print(f"[calc_saveResult] error: {e}")


# ---------- Main Window with Tabs ----------
class MainDensityWindow(QWidget):
    """Main window holding two tabs: Area Fraction and Diff Result."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("[CSB-MGH] Density Tracking")
        self.setGeometry(550, 150, 1200, 1000)

        self.tabs = QTabWidget(self)
        self.area_tab = densityEstimation()
        self.diff_tab = densityTracking()
        self.tabs.addTab(self.area_tab, "Area Fraction")
        self.tabs.addTab(self.diff_tab, "Diff Result")

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainDensityWindow()
    main_window.show()
    sys.exit(app.exec_())
