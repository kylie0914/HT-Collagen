# HT-Collagen

**Fiber migration analysis tool** for collagen microscopy image sequences.

## Workflow

1. **Image preprocessing** — batch processing with an ImageJ macro.
2. **Drift correction** — FFT-based alignment of TIFF sequences.
3. **Density analysis** — area-fraction heatmaps and image-to-image difference maps.
4. **PIVlab** — launch an external PIVlab installation for optical-flow analysis.
5. **Animation export** — convert PNG sequences to GIF or MP4.

## Project layout

```text
HT-Collagen/
├── src/
│   ├── main.py
│   ├── image_processing/
│   ├── drift_correction/
│   ├── density_analysis/
│   ├── pivlab/
│   └── utils/
├── resources/
├── data/
├── archive/
├── README.md
├── requirements.txt
└── .gitignore
```

The `src/` modules currently provide organized entry points around the original root-level analysis scripts. The original scripts are intentionally retained for compatibility; no legacy scripts or user data were deleted in this cleanup.

## Requirements

- Python 3
- Packages in [`requirements.txt`](requirements.txt)
- ImageJ/Fiji and Java for the ImageJ processing step
- PIVlab installed separately; choose its executable in the application

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run

From the repository root:

```bash
python -m src.main
```

Launch the PNG animation exporter separately:

```bash
python -m src.utils.png2gif
```

Legacy entry points remain available from the repository root, for example `python p0_main_v3.py` and `python png2gif.py`.

## Data and generated files

Choose microscopy input folders through the application. Processing outputs are written next to or alongside the selected input folders. Keep raw research data, generated analysis outputs, local logs, Python caches, and IDE settings out of version control unless they are deliberately being shared.

Old backups, macro drafts, logs, and IDE metadata have not been deleted or moved by this change. Review those files before archiving or removing them; `.gitignore` only prevents new untracked matching files from being added and does not untrack files already committed.
