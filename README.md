# HT-Collagen

**Fiber migration analysis tool** for processing collagen microscopy image sequences, correcting drift, analyzing density, and launching PIVlab.

## Workflow

1. **Image preprocessing** — batch-process images with an ImageJ macro (background subtraction and thresholding).
2. **Drift correction** — estimate image-sequence drift with FFT-based correlation and save aligned TIFFs.
3. **Density analysis** — generate area-fraction heatmaps and compare two images with a difference map.
4. **PIVlab** — select and launch an external PIVlab executable for optical-flow analysis.
5. **Animation export** — convert a sequence of PNG images to GIF and/or MP4.

The main application is a PyQt5 desktop GUI. Processing outputs are written alongside the selected input folders; keep large microscopy datasets and generated results out of version control unless they are intentionally part of the project.

## Repository contents

```text
HT-Collagen/
├── p0_main_v3.py                 # Main workflow GUI
├── p1_ImageProcessing_macro.py   # ImageJ macro batch-processing GUI
├── p2_drift_correction_v3IB.py   # TIFF drift correction
├── p3_density_tracking.py        # Density heatmap and difference analysis
├── p4_PIVlab.py                  # External PIVlab launcher helpers
├── png2gif.py                    # PNG sequence to GIF / MP4 GUI
├── resources/                    # GUI images and PIVlab resources
├── data/raw/                     # Data directory (keep datasets local/private)
├── README.md
├── requirements.txt
└── .gitignore
```

Legacy scripts, macro drafts, backups, and generated logs are still present at the repository root. They have not been deleted or moved in this documentation cleanup; review them before archiving or removing them.

## Requirements

- Python 3
- Dependencies listed in [`requirements.txt`](requirements.txt)
- ImageJ/Fiji and a working Java installation for the ImageJ batch-processing step
- PIVlab installed separately; the application asks you to select its executable

Install the Python packages:

```bash
python -m pip install -r requirements.txt
```

## Run

Start the main GUI from the repository root:

```bash
python p0_main_v3.py
```

Run the PNG animation exporter separately, if needed:

```bash
python png2gif.py
```

## Notes

- ImageJ/Fiji and PIVlab are external applications and are not installed by `requirements.txt`.
- The ImageJ step writes processed images to `imgj_proc/` under the selected input folder.
- Drift-correction and density-analysis outputs are saved relative to the selected data folder.
- Do not commit raw microscopy data, generated results, crash logs, Python cache files, or local IDE settings unless they are intentionally being shared.
- The repository contains backup scripts and historical files. Git history is the preferred place to preserve prior versions; inspect each file before removing it.
