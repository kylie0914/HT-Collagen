# HT-Collagen

Fiber migration analysis tool for collagen image processing, drift correction, density analysis, and PIV-based force estimation.

## Overview

This project analyzes collagen fiber migration and deformation from image sequences using a multi-step workflow:

1. Image preprocessing
2. Drift correction
3. Density / area-fraction analysis
4. Optical flow / PIV-based analysis

The workflow is implemented as a Qt-based Python GUI and uses ImageJ / Fiji for batch image processing.

## Project workflow

- Image processing
  - Background subtraction
  - Threshold masking
  - Batch processing for image sequences

- Drift correction
  - FFT-based frame alignment
  - ROI-based correction for image registration

- Density analysis
  - Area-fraction estimation
  - Heatmap generation
  - Difference map analysis

- Force analysis
  - PIVlab integration
  - Optical flow-based stress / force estimation

## Repository structure

```text
HT-Collagen/
├── README.md
├── requirements.txt
├── .gitignore
├── p0_main_v3.py
├── p1_ImageProcessing_macro.py
├── p2_drift_correction_v3IB.py
├── p3_density_tracking.py
├── p4_PIVlab.py
├── png2gif.py
├── resources/
│   ├── 0_CSB_logo.jpg
│   ├── 0_CSB_logo_v1.png
│   ├── 1_down_arrow.png
│   └── PIVlab/
├── data/
│   ├── raw/
│   ├── processed/
│   └── results/
├── archive/
│   ├── backup/
│   ├── notes/
│   └── old_scripts/
├── output/
│   └── figures/
└── notes/
```

## Setup

### Python environment

Install dependencies:

```bash
pip install -r requirements.txt
```

Typical dependencies include:
- PyQt5
- OpenCV
- NumPy
- SciPy
- Matplotlib
- Pillow
- scikit-learn
- pyimagej

### ImageJ / Fiji

For batch processing, ensure ImageJ or Fiji is available and configured for `pyimagej`.

## Usage

Run the main GUI:

```bash
python p0_main_v3.py
```

Or run modules individually:

```bash
python p1_ImageProcessing_macro.py
python p2_drift_correction_v3IB.py
python p3_density_tracking.py
python p4_PIVlab.py
python png2gif.py
```

## Outputs

The pipeline generates:
- processed TIFF images
- drift-corrected image sequences
- density heatmaps
- difference maps
- exported GIF / MP4 animations
- experimental summary CSVs

## Notes

- Keep raw microscopy data under `data/raw`.
- Save processed outputs under `data/processed` or `data/results`.
- Archive old scripts and backup files under `archive/`.
- Do not commit generated temporary files, logs, or IDE metadata.

## Project context

This repository was developed for collagen fiber migration analysis and related image-based mechanical quantification workflows.
