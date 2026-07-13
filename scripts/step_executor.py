import sys
import argparse
import os

def get_step_instructions(step, working_folder_file):
    target_dir = "[TARGET_DIRECTORY]"
    if os.path.exists(working_folder_file):
        with open(working_folder_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                # Ensure we display forward slashes
                target_dir = content.replace("\\", "/")

    params_A = "128"
    params_B = "255"
    params_C = "255"
    params_D = "0"
    params_str = f"--grayscale-method average --binarize-min {params_A} --binarize-max {params_B} --value-inside {params_C} --value-outside {params_D}"
    
    if os.path.exists("param_extract_paths.txt"):
        with open("param_extract_paths.txt", "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                params_str = content

    steps = {
        1: f"""
========================================================================
【Step 1】 Path Extraction (Vector Conversion)
========================================================================
[Objective]
Extract vector paths from the original image, generating metadata and SVGs.

[Execution Instructions for AI]
1. Must use "--prefix 01_raw".
2. Ensure the user has specified an image.
3. If binarization parameters (--grayscale-method, --binarize-min, --binarize-max, --value-inside) are not specified by the user, inform the user of the AI-selected default values.
4. If everything is fine, execute the following:
   python scripts/extract_paths.py Inputs/[ImageFileNameWithoutExtension].[Extension] Outputs --prefix 01_raw --grayscale-method average --binarize-min 128 --binarize-max 255 --value-inside 255 --value-outside 0
5. Verify that `param_extract_paths.txt` has been generated.
6. Verify that `{working_folder_file}` has been generated, read it, and confirm the working folder path.
7. Verify that the following files are output in the working folder:
  - 01_raw_metadata.json (JSON file containing bounding boxes and colors of paths)
  - 01_raw_combined.svg (Single SVG file combining all extracted paths)
  - 01_raw_svgs/ (Directory containing individual SVGs for each path)
  - 01_raw_original.png (Copy of the original image)
8. If all looks good, execute `python scripts/step_executor.py 2 {working_folder_file}`.

[Caution for AI]
- If there is an issue, STOP and report.
""",
        2: f"""
========================================================================
【Step 2】 Text Region Extraction
========================================================================
[Objective]
Identify bounding boxes of likely text regions based on the path metadata.

[Execution Instructions for AI]
1. Read `{working_folder_file}` and confirm the working folder path.
2. Ensure `01_raw_metadata.json` and `01_raw_original.png` exist in the working folder.
3. If fine, execute the following:
   python scripts/analyze_text_regions.py -m {target_dir}/01_raw_metadata.json -o {target_dir}/02_text_lines.json
4. Verify that `02_text_lines.json` was created in the working folder.
5. If fine, execute the following:
   python scripts/draw_text_roi.py -i {target_dir}/01_raw_original.png -j {target_dir}/02_text_lines.json -o {target_dir}/02_text_roi.png
6. Verify that `02_text_roi.png` exists in the working folder.
7. If all looks good, execute `python scripts/step_executor.py 3 {working_folder_file}`.

[Caution for AI]
- If there is an issue, STOP and report.
""",
        3: f"""
========================================================================
【Step 3】 OCR and Self-Correction by AI (Core Hybrid Processing)
========================================================================
[Objective]
AI visually inspects the image, reads text, and updates the JSON.

[Execution Instructions for AI]
1. Read `{working_folder_file}` and confirm the working folder path.
2. Verify that `02_text_roi.png` exists in the working folder.
3. AI (you) must use the `view_file` tool to visually inspect `02_text_roi.png` directly.
4. Perform OCR and create the dictionary JSON:
   Read the text corresponding to each number.
   [CRITICAL] NEVER forcefully read misidentified icons or logos meant to be kept as raster (e.g., white text on background color where the box is clearly smaller than the string). Always set them to an empty string `""`!
   Save the result to `temp_scripts/ocr.json`.
5. Update JSON:
   python scripts/update_text_lines.py -j {target_dir}/02_text_lines.json -d temp_scripts/ocr.json
6. If all looks good, execute `python scripts/step_executor.py 4 {working_folder_file}`.

[Caution for AI]
- If there is an issue, STOP and report.
""",
        4: f"""
========================================================================
【Step 4】 Erase Text Regions (Fill with Background Color)
========================================================================
[Objective]
Fill only the regions identified as text via OCR with the background color, creating a clean underlay.

[Execution Instructions for AI]
1. Read `{working_folder_file}` and confirm the working folder path.
2. Verify that `01_raw_original.png` and `02_text_lines.json` exist in the working folder.
3. If fine, execute the following:
   python scripts/erase_text_regions.py -i {target_dir}/01_raw_original.png -j {target_dir}/02_text_lines.json -o {target_dir}/03_notext.png
4. Verify that `03_notext.png` exists in the working folder.
5. If all looks good, execute `python scripts/step_executor.py 5 {working_folder_file}`.

[Caution for AI]
- If there is an issue, STOP and report.
""",
        5: f"""
========================================================================
【Step 5】 Path Extraction from Text-Erased Image
========================================================================
[Objective]
Extract paths again from the text-erased image to obtain pure vector paths for illustration components.

[Execution Instructions for AI]
1. Read `{working_folder_file}` and confirm the working folder path.
2. Read `param_extract_paths.txt` and confirm the arguments.
3. Verify that `03_notext.png` and `02_text_lines.json` exist in the working folder.
4. If fine, execute the following (using the binarization parameters read in step 2):
   python scripts/extract_paths.py {target_dir}/03_notext.png {target_dir} --prefix 05_notext --force {params_str}
5. Verify that the following files are output in the working folder:
  - 05_notext_metadata.json (JSON file with bounding boxes and colors)
  - 05_notext_combined.svg (Combined SVG)
  - 05_notext_svgs/ (Individual SVGs folder)
  - 05_notext_original.png (Copy of the image)
6. If all looks good, execute `python scripts/step_executor.py 6 {working_folder_file}`.

[Caution for AI]
- If there is an issue, STOP and report.
""",
        6: f"""
========================================================================
【Step 6】 Component Clustering
========================================================================
[Objective]
Calculate path overlaps and automatically compute bounding boxes for meaningful component groups.

[Execution Instructions for AI]
1. Read `{working_folder_file}` and confirm the working folder path.
2. Verify that `05_notext_metadata.json` exists in the working folder.
3. If fine, execute the following:
   python scripts/auto_cluster.py -m {target_dir}/05_notext_metadata.json -o {target_dir}/06_crop_config.json -v {target_dir}/06_cluster_visual.png
4. Verify that `06_crop_config.json` and `06_cluster_visual.png` are generated.
5. AI must visually inspect `06_cluster_visual.png` and confirm that components are correctly separated.
6. If all looks good, execute `python scripts/step_executor.py 7 {working_folder_file}`.

[Caution for AI]
- If there is an issue, STOP and report.
""",
        7: f"""
========================================================================
【Step 7】 Crop Illustration Images
========================================================================
[Objective]
Crop illustrations from the image based on the component bounding boxes determined in Step 6 (`06_crop_config.json`) and save them.

[Execution Instructions for AI]
1. Read `{working_folder_file}` and confirm the working folder path.
2. Verify that `05_notext_original.png` and `06_crop_config.json` exist in the working folder.
3. If fine, execute the following:
   python scripts/crop_illustrations.py -c {target_dir}/06_crop_config.json -s {target_dir}/05_notext_original.png -d {target_dir}/07_crops
4. Verify that `07_crops/*.png` files are generated.
5. If all looks good, execute `python scripts/step_executor.py 8 {working_folder_file}`.

[Caution for AI]
- If there is an issue, STOP and report.
- [GOLDEN RULE] NEVER force characters or icons to be represented as vector paths! Do not handle vector paths directly for them!
""",
        8: f"""
========================================================================
【Step 8】 Build Final SVG
========================================================================
[Objective]
Combine the cropped PNG images and the AI-extracted text to complete the final SVG.

[Execution Instructions for AI]
1. Read `{working_folder_file}` and confirm the working folder path.
2. Verify that `05_notext_combined.svg`, `06_crop_config.json`, `02_text_lines.json`, and `07_crops/` exist in the working folder.
3. If fine, execute the following:
   python scripts/build_final_svg.py -b {target_dir}/05_notext_combined.svg -c {target_dir}/06_crop_config.json -t {target_dir}/02_text_lines.json -i {target_dir}/07_crops -o {target_dir}/08_final.svg
4. Verify that `08_final.svg` is generated.

[Caution for AI]
- This is the final step. After completion, report the outcome to the user.
"""
    }
    
    if step in steps:
        print(steps[step])
    else:
        print(f"[ERROR] Valid step numbers are 1 to {max(steps.keys())}.")

def main():
    parser = argparse.ArgumentParser(description="AI Vector SVG Pipeline - Step Executor")
    parser.add_argument("step", type=int, help="Step number to execute (1-8)")
    parser.add_argument("working_folder_file", type=str, help="Path to the file containing the current working folder (e.g., current_working_folder.txt)")
    args = parser.parse_args()
    
    get_step_instructions(args.step, args.working_folder_file)

if __name__ == "__main__":
    main()
