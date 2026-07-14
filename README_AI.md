# AI Vector SVG Preparation - Developer Instructions & Pipeline Guidelines (README_AI.md)

This document establishes the official specifications, folder architecture, script management rules, and development guidelines for the image processing and hybrid SVG reconstruction pipeline.

---

## 1. Project Directory Structure & Script Rules

To keep the repository clean and maintainable, all scripts and artifacts are strictly organized as follows:

```
AIVectorPrep/
│
├── Inputs/                         # Raw input raster images (PNG, JPG, etc.)
│   └── [basename].png
│
├── Outputs/                        # Outputs categorized by task directory
│   └── [basename]_XXX/             # E.g., demo008_001/ (auto-generated folder)
│
├── scripts/                        # Production & Pipeline scripts
│   ├── step_executor.py            # Orchestrator (step instructions)
│   ├── extract_paths.py            # Binarization and Potrace vector extraction
│   ├── analyze_text_regions.py     # Detect bounding boxes of text regions
│   ├── draw_text_roi.py            # Annotate image with numbered text bounding boxes
│   ├── update_text_lines.py        # Update metadata JSON with OCR result strings
│   ├── erase_text_regions.py       # Blank out text regions with background color
│   ├── auto_cluster.py             # Cluster remaining visual elements into components
│   ├── crop_illustrations.py       # Crop components as raster PNGs
│   └── build_final_svg.py          # Compile base SVG + cropped PNGs + overlaid text
│
├── temp_scripts/                   # Sandbox for one-off/temporary scripts
│
├── current_working_folder.txt      # Tracks the currently active output directory (forward slashes)
└── param_extract_paths.txt         # Tracks the binarization arguments used in Step 1
```

### Script Management Rules
- **Production Scripts (`scripts/`)**: Highly reusable, parameterized, and generic code. No hardcoded file paths or directory configurations. Must be placed in the `scripts/` directory.
- **Temporary Sandbox (`temp_scripts/`)**: For experimentations, testing scripts, or one-off tasks. Scripts in this folder can be created freely, but they must NOT interfere with the main pipeline.

---

## 2. Core Tool Specifications

### [scripts/step_executor.py](file:///c:/UserData/nishida/Git/AIVectorPrep/scripts/step_executor.py) (Orchestrator)
Provides instructions and automatically builds parameter-injected command lines for each of the 8 steps. It relies on the dynamic working directory and parameter text files.
- **Usage**: `python scripts/step_executor.py [1-8] current_working_folder.txt`

### [scripts/extract_paths.py](file:///c:/UserData/nishida/Git/AIVectorPrep/scripts/extract_paths.py)
Executes image binarization and runs Potrace to extract vector paths. Outputs path geometry and metadata.
- Automatically handles new version directory generation under `Outputs/` during Step 1.
- Tracks output state in `current_working_folder.txt` (normalized with forward slashes) and `param_extract_paths.txt`.

### [scripts/analyze_text_regions.py](file:///c:/UserData/nishida/Git/AIVectorPrep/scripts/analyze_text_regions.py)
Analyzes `01_raw_metadata.json` to identify bounding boxes of text lines using physical layout properties.

### [scripts/draw_text_roi.py](file:///c:/UserData/nishida/Git/AIVectorPrep/scripts/draw_text_roi.py)
Draws bounding boxes and numbers them on the original image to output `02_text_roi.png` for OCR visual reference.

### [scripts/update_text_lines.py](file:///c:/UserData/nishida/Git/AIVectorPrep/scripts/update_text_lines.py)
Injects OCR text from a dictionary JSON (`temp_scripts/ocr.json`) back into the metadata JSON.

### [scripts/erase_text_regions.py](file:///c:/UserData/nishida/Git/AIVectorPrep/scripts/erase_text_regions.py)
Fills text bounding boxes in the original image with the sampled background color, generating a text-free base image (`03_notext.png`).

### [scripts/auto_cluster.py](file:///c:/UserData/nishida/Git/AIVectorPrep/scripts/auto_cluster.py)
Analyzes vector path bounding boxes from the text-free image and groups overlapping/adjacent paths into logical component boxes (`06_crop_config.json`).

### [scripts/crop_illustrations.py](file:///c:/UserData/nishida/Git/AIVectorPrep/scripts/crop_illustrations.py)
Crops raster illustrations/components from the image using the coordinate configs from Step 6, outputting PNG parts.

### [scripts/build_final_svg.py](file:///c:/UserData/nishida/Git/AIVectorPrep/scripts/build_final_svg.py)
Aggregates the base vector SVG, cropped illustration PNGs (encoded as Base64 `<image>`), and OCRed text (`<text>` tags) into a final single SVG file.

---

## 3. Dynamic State & Parameters

To ensure generality and prevent manual errors, the pipeline uses two state tracking files in the root folder:
1. **`current_working_folder.txt`**: Records the absolute/relative output directory path of the active task (e.g. `Outputs/demo008_001`). **Must always use forward slashes `/`** to prevent escape-character bugs on Windows.
2. **`param_extract_paths.txt`**: Records the exact binarization parameters (e.g., `--grayscale-method average --binarize-min 180...`) determined during Step 1. These parameters are dynamically retrieved in Step 5 for consistent path extraction.

---

## 4. Standard Workflow (The 8 Steps)

The AI Agent must execute the pipeline sequentially, using the orchestrator for reference:

1. **Step 1: Raw Path Extraction**
   - Extract raw vector paths. Generates `01_raw_*` outputs and sets up the active directory.
2. **Step 2: Text BBox Analysis**
   - Locate candidate text lines. Generates `02_text_lines.json` and the ROI visual reference `02_text_roi.png`.
3. **Step 3: OCR and Correction (Hybrid Loop)**
   - AI visually inspects `02_text_roi.png`.
   - **Crucial Rule**: Forcefully read ONLY real text. Icons and logos (e.g., logos with white text on background color where bounding box is too small) MUST be left as empty string `""` to preserve them as raster graphics.
   - Run `update_text_lines.py` to merge OCR results.
4. **Step 4: Text Erasure**
   - Fill OCRed text regions with background color, yielding `03_notext.png`.
5. **Step 5: Illustration Path Extraction**
   - Re-run path extraction on the text-free image using the original parameters. Generates `05_notext_*` files.
6. **Step 6: Component Clustering**
   - Group overlapping paths. Generates `06_crop_config.json` and a visual representation `06_cluster_visual.png`.
   - AI must visually inspect `06_cluster_visual.png` to confirm clustering quality.
7. **Step 7: Illustration Cropping**
   - Crop illustration components to `07_crops/`.
8. **Step 8: SVG Compilation**
   - Assemble `08_final.svg` containing vector layout, raster PNGs, and text tags.

---

## 5. Golden Rules for AI Agent

### [Rule 1] Never Vectorize Illustrations and Icons
Illustrations, human figures, logos, and complex icons must NEVER be represented as direct vector paths (which results in messy, uneditable outlines). They must be cropped as raster PNGs in Step 7 and integrated using `<image>` tags. Vector paths should only represent shapes like speech bubble borders, arrows, stars, or simple backdrops.

### [Rule 2] Respect Coordinate Integrity
Do not modify or guess bounding box coordinates manually. Always use the computed coordinates from the JSON configs.

### [Rule 3] Ensure Cross-Platform Image Rendering
All `<image>` tags in the reconstructed SVG must include both `href` and `xlink:href` attributes with the base64-encoded PNG content. This ensures correct rendering across modern web browsers, MS Office, and vector editors.

---

## 6. Command-Line Arguments Specification

This section documents the detailed command-line interface (CLI) options for each core Python script under `scripts/`.

### 1. `scripts/step_executor.py`
Executes instructions and prints command suggestions for each step.
* **Arguments:**
  - `step` (positional, `int`, required): The step number to retrieve instructions for (`1` to `8`).
  - `working_folder_file` (positional, `str`, required): Path to the state tracking file (usually `current_working_folder.txt`).

---

### 2. `scripts/extract_paths.py`
Processes an image (binarization, thresholding) and extracts vector paths using Potrace.
* **Arguments:**
  - `INPUT_IMAGE` (positional, `str`, required): Path to the input image file.
  - `OUTPUT_DIRECTORY` (positional, `str`, required): Output directory path (will create a subdirectory `[basename]_XXX` inside).
  - `--prefix` (`str`, default: `01_raw`): Prefix name for the generated output files (e.g. `05_notext`).
  - `--force` (flag): Overwrites existing outputs if the destination directory exists.
  - `--grayscale-method` (`str`, choices: `["average", "luminosity", "lightness", "r", "g", "b", "h", "s", "v"]`, default: `"average"`): Method to convert color image to grayscale.
  - `--binarize-min` (`int`, default: `128`): Lower threshold for binarization (0-255).
  - `--binarize-max` (`int`, default: `255`): Upper threshold for binarization (0-255).
  - `--value-inside` (`int`, default: `255`): Grayscale pixel values in the range `[binarize-min, binarize-max]` will be mapped to this value.
  - `--value-outside` (`int`, default: `0`): Grayscale pixel values outside the range will be mapped to this value.

---

### 3. `scripts/analyze_text_regions.py`
Locates potential text lines from vector path metadata using clustering.
* **Arguments:**
  - `-m`, `--metadata` (`str`, required): Path to input `metadata.json` (output from `extract_paths.py`).
  - `-o`, `--output` (`str`, default: auto-generated): Path to save `text_lines.json`.
  - `--area-max` (`float`): Maximum bounding box area ($px^2$) to consider a path part of a character (default: auto-calculated).
  - `--area-min` (`float`, default: `30.0`): Minimum bounding box area ($px^2$) to filter out noise.
  - `--dim-max` (`float`): Maximum dimension (length of longest side, $px$) for a character path (default: auto-calculated).
  - `--line-tol` (`float`): Horizontal row alignment tolerance ($px$) in Y direction (default: auto-calculated).
  - `--char-gap` (`float`): Max horizontal distance ($px$) between characters in the same text block (default: auto-calculated).
  - `--min-paths` (`int`, default: `3`): Minimum number of adjacent paths to qualify as a text line.
  - `--scale` (`float`, default: `1.0`): Scale factor applied to all auto-calculated thresholds.
  - `-v`, `--verbose` (flag): Enables verbose logging.

---

### 4. `scripts/draw_text_roi.py`
Annotates the original image with red bounding boxes and index labels for OCR reference.
* **Arguments:**
  - `-i`, `--image` (`str`, required): Path to the original input image.
  - `-j`, `--json` (`str`, required): Path to the `text_lines.json` metadata.
  - `-o`, `--output` (`str`, required): Destination path for the annotated ROI image (e.g. `02_text_roi.png`).

---

### 5. `scripts/update_text_lines.py`
Merges OCR text from a key-value dictionary JSON into the main text lines metadata JSON.
* **Arguments:**
  - `-j`, `--json` (`str`, required): Path to the `text_lines.json` file.
  - `-d`, `--dictionary` (`str`, required): Path to the OCR dictionary JSON file (e.g., `temp_scripts/ocr.json`).

---

### 6. `scripts/erase_text_regions.py`
Blanks out detected text regions on the original image using local background color sampling.
* **Arguments:**
  - `-i`, `--input` (`str`, required): Path to the original image.
  - `-j`, `--json` (`str`, required): Path to the updated `text_lines.json` containing text strings.
  - `-o`, `--output` (`str`, required): Destination path for the text-erased underlay image.

---

### 7. `scripts/auto_cluster.py`
Calculates overlapping vector paths on the text-erased image to output component crop configurations.
* **Arguments:**
  - `-m`, `--metadata` (`str`, required): Path to the binarized illustration `metadata.json` (Step 5 output).
  - `-o`, `--output` (`str`, required): Destination path for the crop configuration JSON (e.g. `06_crop_config.json`).
  - `-v`, `--visualize` (`str`): Destination path to save the component bounding box visualization image (e.g. `06_cluster_visual.png`).
  - `--margin` (`int`, default: `5`): Pixel margin to expand path bounding boxes before calculating overlaps.
  - `--threshold` (`float`, default: `0.2`): Area overlap ratio threshold to cluster paths together.

---

### 8. `scripts/crop_illustrations.py`
Crops individual raster PNG components from the original clean image.
* **Arguments:**
  - `-c`, `--config` (`str`, required): Path to the `crop_config.json` containing coordinates.
  - `-s`, `--source` (`str`): Override path to the source image (defaults to value inside config JSON).
  - `-d`, `--dest` (`str`): Override destination directory to store cropped PNG files (defaults to value inside config JSON).

---

### 9. `scripts/build_final_svg.py`
Assembles base vector lines, base64-encoded cropped illustration PNGs, and OCRed text.
* **Arguments:**
  - `-b`, `--base-svg` (`str`, required): Path to the base combined vector SVG (from Step 5).
  - `-c`, `--crop-config` (`str`, required): Path to `crop_config.json` (from Step 6).
  - `-t`, `--text-lines` (`str`, required): Path to updated `text_lines.json` (containing OCR results).
  - `-i`, `--image-dir` (`str`, required): Path to the directory containing cropped PNGs (from Step 7).
  - `-o`, `--output` (`str`, required): Destination path for the completed final SVG file (e.g. `08_final.svg`).

