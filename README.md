# HT-Collagen

**Fiber migration analysis tool** for collagen microscopy image sequences.

## Workflow

1. **Image preprocessing** — batch processing with an ImageJ macro.
2. **Drift correction** — FFT-based alignment of TIFF sequences.
3. **Density analysis** — area-fraction heatmaps and image-to-image difference maps.
4. **PIVlab** — launch an external PIVlab installation for optical-flow analysis.
5. **Animation export** — convert PNG sequences to GIF or MP4.

## Run

Install Python dependencies from the repository root:

```bash
python -m pip install -r requirements.txt
```

Launch the reorganized desktop GUI from the repository root:

```bash
python -m src.main
```

The legacy command remains available:

```bash
python p0_main_v3.py
```

Launch the PNG animation exporter separately:

```bash
python -m src.utils.png2gif
```

ImageJ/Fiji (with Java) is required for batch preprocessing. PIVlab is an external application; select its executable when prompted.

## Repository layout

```text
HT-Collagen/
├── src/                         # Organized application entry points
│   ├── main.py
│   ├── image_processing/
│   ├── drift_correction/
│   ├── density_analysis/
│   ├── pivlab/
│   └── utils/
├── resources/                   # GUI assets and bundled PIVlab files
├── data/raw/                    # Existing sample and research data
├── archive/                     # Reserved for reviewed historical files
├── p0_main_v3.py                # Backward-compatible launcher
├── p1_ImageProcessing_macro.py  # Existing ImageJ batch GUI implementation
├── p2_drift_correction_v3IB.py  # Existing drift-correction implementation
├── p3_density_tracking.py       # Existing density-analysis implementation
├── p4_PIVlab.py                 # Existing PIVlab launcher implementation
├── png2gif.py                   # Existing animation exporter implementation
├── requirements.txt
└── .gitignore
```

The `src/` modules provide organized entry points while the original root-level analysis implementations remain in place for backward compatibility. This cleanup does not delete or relocate research data, backups, logs, or IDE metadata. Review these items before removing them; some may already be tracked in Git.

## Data and generated files

Choose microscopy input folders through the application. Processed images and analysis outputs are generally written next to or alongside the selected folder. The repository currently contains sample data and generated analysis artifacts under `data/raw/`; do not assume that directory is empty or safe to remove. Keep new raw research data and generated output out of version control unless they are intentionally being shared.
