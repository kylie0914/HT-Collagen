# p2_drift_correction_v3IB_tiff.py
# -*- coding: utf-8 -*-
"""
Drift correction for a sequence of TIFF images (supports 16-bit).
- Pick a folder with output images from Image Processing step (TIF/TIFF).
- Select a crop ROI by clicking two points (top-left and bottom-right) on the first image.
- Compute frame-to-frame drift via phase correlation on 8-bit copies.
- Apply integer-pixel shift to the ORIGINAL dtype image and save as TIFF.

Dependencies:
  - numpy, opencv-python, matplotlib, scipy
"""

import os
import re
import sys
import pickle
import numpy as np
import cv2
from tkinter import filedialog, Tk
from scipy.fft import fft2, ifft2, fftshift
import matplotlib.pyplot as plt


# -------- Utils --------
def get_directory():
    root = Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory(title="Choose a folder containing the TIFF image sequence")
    root.destroy()
    return folder_selected

def to_uint8_contrast(img):
    """Convert any uint8/uint16 (or float) image into contrast-stretched uint8 for correlation."""
    arr = img.astype(np.float32)
    mn, mx = float(arr.min()), float(arr.max())
    if mx <= mn:
        return np.zeros_like(arr, dtype=np.uint8)
    arr = (arr - mn) / (mx - mn) * 255.0
    return arr.astype(np.uint8)

_num_re = re.compile(r'(\d+)')
def natural_key(s: str):
    """Natural sort key: split digits as integers"""
    return [int(text) if text.isdigit() else text.lower() for text in _num_re.split(s)]

def extract_trailing_number(fname: str, fallback_idx: int = None) -> str:
    """
    extract the number in front of ".tif"
    """
    m = re.search(r'(\d+)(?=\.tif{1,2}$)', fname, re.IGNORECASE)
    if m:
        return m.group(1)
    else:
        return str(fallback_idx) if fallback_idx is not None else os.path.splitext(fname)[0]

def list_images(input_dir, exts=(".tif", ".tiff")):
    files = [f for f in os.listdir(input_dir) if f.lower().endswith(exts)]
    files.sort(key=natural_key)
    return files

def pick_roi(image_8bit):
    """
    Let user pick ROI:
    - Click TOP-LEFT corner first
    - Then click BOTTOM-RIGHT corner
    The ROI (x, y, w, h) will be used for drift correlation.
    """
    plt.figure("Pick ROI: select top-left and bottom-right")
    plt.imshow(image_8bit, cmap='gray')
    plt.title("Click TOP-LEFT and BOTTOM-RIGHT, then close window")
    pts = plt.ginput(2, timeout=0)  # wait until 2 clicks, no timeout
    plt.close()
    if len(pts) != 2:
        raise RuntimeError("Exactly two points must be selected.")
    (x1, y1), (x2, y2) = pts
    x1, y1, x2, y2 = int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2))
    x0, y0 = min(x1, x2), min(y1, y2)
    w, h = abs(x2 - x1), abs(y2 - y1)
    if w <= 0 or h <= 0:
        raise ValueError(f"Invalid crop area: width={w}, height={h}")
    return (x0, y0, w, h)


# -------- Main --------
def main():
    inputpath = get_directory()
    if not inputpath:
        print("No folder selected. Exiting.")
        sys.exit(0)

    files = list_images(inputpath, exts=(".tif", ".tiff"))
    nFrames = len(files)
    if nFrames == 0:
        print("No .tif/.tiff files found in the directory.")
        sys.exit(0)

    print(f"Found {nFrames} TIFFs in: {inputpath}")
    print("Loading reference frame...")

    # Reference frame (original dtype preserved)
    ref_path = os.path.join(inputpath, files[0])
    imageref = cv2.imread(ref_path, cv2.IMREAD_UNCHANGED)  # supports 8/16-bit
    if imageref is None:
        raise RuntimeError(f"Failed to read: {ref_path}")

    # For correlation, make an 8-bit contrast-stretched copy
    imageref_u8 = to_uint8_contrast(imageref)

    # Ask user to pick ROI once on the 8-bit reference
    roi = pick_roi(imageref_u8)
    x0, y0, w, h = roi
    print(f"ROI = (x={x0}, y={y0}, w={w}, h={h})")

    # Crop reference (use 8-bit for FFT)
    ref_crop_u8 = imageref_u8[y0:y0 + h, x0:x0 + w]
    if ref_crop_u8.size == 0:
        raise RuntimeError("Empty ROI crop from reference frame.")

    fft_ref = fft2(ref_crop_u8)
    vidHeight, vidWidth = ref_crop_u8.shape
    centery, centerx = (vidHeight // 2, vidWidth // 2)

    drift_y = np.zeros(nFrames, dtype=np.float32)
    drift_x = np.zeros(nFrames, dtype=np.float32)

    print("Estimating drift for each frame...")
    for i, filename in enumerate(files):
        fpath = os.path.join(inputpath, filename)
        img = cv2.imread(fpath, cv2.IMREAD_UNCHANGED)
        if img is None:
            raise RuntimeError(f"Failed to read: {fpath}")

        # Use 8-bit contrast copy for correlation
        img_u8 = to_uint8_contrast(img)
        img_crop_u8 = img_u8[y0:y0 + h, x0:x0 + w]

        # FFT-based cross-correlation
        fft_frame = fft2(img_crop_u8)
        prod = fft_ref * np.conj(fft_frame)
        cc = ifft2(prod)
        cc_shifted = fftshift(cc)

        maxy, maxx = np.unravel_index(np.argmax(np.abs(cc_shifted)), cc_shifted.shape)
        dy = float(maxy - centery)
        dx = float(maxx - centerx)

        # Unwrap jumps across the periodic boundary
        if i > 0:
            if abs(dy - drift_y[i - 1]) > vidHeight / 2:
                dy -= np.sign(dy - drift_y[i - 1]) * vidHeight
            if abs(dx - drift_x[i - 1]) > vidWidth / 2:
                dx -= np.sign(dx - drift_x[i - 1]) * vidWidth

        drift_y[i] = dy
        drift_x[i] = dx

        if (i + 1) % 5 == 0 or i == nFrames - 1:
            print(f"  [{i + 1}/{nFrames}] dy={dy:.2f}, dx={dx:.2f}")

    # Save drift vectors
    savepath = os.path.join(inputpath, "../drift_corr")
    os.makedirs(savepath, exist_ok=True)
    shiftdatafilename = os.path.join(savepath, f"{os.path.splitext(files[0])[0]}_driftdata.pkl")
    with open(shiftdatafilename, 'wb') as f:
        pickle.dump({'nFrames': int(nFrames), 'drift_y': drift_y, 'drift_x': drift_x, 'roi': roi}, f)
    print(f"Drift data saved: {shiftdatafilename}")

    # Apply drift to ORIGINAL dtype image & save as TIFF
    print("Applying drift and saving shifted images (TIFF)...")
    for i, filename in enumerate(files):
        fpath = os.path.join(inputpath, filename)
        img = cv2.imread(fpath, cv2.IMREAD_UNCHANGED)  # keep original dtype (uint16 if 16-bit)
        if img is None:
            raise RuntimeError(f"Failed to read: {fpath}")

        # Integer-pixel roll (y then x). Positive dy shifts down (axis=0), positive dx shifts right (axis=1).
        shifted = np.roll(img, int(drift_y[i]), axis=0)
        shifted = np.roll(shifted, int(drift_x[i]), axis=1)

        # Save as TIFF with similar base name
        # base = os.path.splitext(filename)[0]
        tail = extract_trailing_number(filename, fallback_idx=i)
        out_name = f"{tail}.tif"
        out_path = os.path.join(savepath, out_name)


        # Use cv2 to write; ensure proper dtype is kept (uint16 will be saved as 16-bit TIFF)
        ok = cv2.imwrite(out_path, shifted)
        if not ok:
            raise RuntimeError(f"Failed to save: {out_path}")

        if (i + 1) % 5 == 0 or i == nFrames - 1:
            print(f"  [{i + 1}/{nFrames}] saved: {out_name}")

    print("Drift correction completed.")

if __name__ == "__main__":
    main()
