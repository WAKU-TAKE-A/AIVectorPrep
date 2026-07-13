import os
import json
import argparse
import sys
import xml.etree.ElementTree as ET

def build_parser():
    parser = argparse.ArgumentParser(description="Build the final SVG by overlaying PNG crops and text onto the combined vector SVG.")
    parser.add_argument("-b", "--base-svg", required=True, help="Base combined SVG file (e.g. 04_notext_combined.svg)")
    parser.add_argument("-c", "--crop-config", required=True, help="Crop config JSON (e.g. 05_crop_config.json)")
    parser.add_argument("-t", "--text-lines", required=True, help="OCR text JSON (e.g. 02_text_lines.json)")
    parser.add_argument("-i", "--image-dir", required=True, help="Directory containing cropped PNGs (e.g. 06_crops)")
    parser.add_argument("-o", "--output", required=True, help="Output final SVG file (e.g. 07_final.svg)")
    return parser

def main():
    args = build_parser().parse_args()

    # Verify files exist
    for filepath in [args.base_svg, args.crop_config, args.text_lines]:
        if not os.path.exists(filepath):
            print(f"[ERROR] File not found: {filepath}", file=sys.stderr)
            sys.exit(1)
            
    if not os.path.isdir(args.image_dir):
        print(f"[ERROR] Image directory not found: {args.image_dir}", file=sys.stderr)
        sys.exit(1)

    # 1. Parse base SVG
    try:
        ET.register_namespace('', "http://www.w3.org/2000/svg")
        ET.register_namespace('xlink', "http://www.w3.org/1999/xlink")
        tree = ET.parse(args.base_svg)
        root = tree.getroot()
    except Exception as e:
        print(f"[ERROR] Failed to parse base SVG: {e}", file=sys.stderr)
        sys.exit(1)

    # Calculate relative path from output directory to image directory
    out_dir = os.path.dirname(args.output)
    if not out_dir:
        out_dir = "."
    rel_image_dir = os.path.relpath(args.image_dir, out_dir)

    # 2. Add Images from crop_config
    with open(args.crop_config, "r", encoding="utf-8") as f:
        crop_config = json.load(f)

    for region in crop_config.get("regions", []):
        label = region["label"]
        bbox = region["bbox"]
        x, y, w, h = bbox
        
        # Use forward slashes for SVG hrefs
        img_path = f"{rel_image_dir}/{label}.png".replace("\\\\", "/")
        
        img_elem = ET.Element("{http://www.w3.org/2000/svg}image")
        img_elem.set("x", str(x))
        img_elem.set("y", str(y))
        img_elem.set("width", str(w))
        img_elem.set("height", str(h))
        img_elem.set("href", img_path)
        img_elem.set("{http://www.w3.org/1999/xlink}href", img_path)
        
        root.append(img_elem)

    # 3. Add Text from text_lines
    with open(args.text_lines, "r", encoding="utf-8") as f:
        text_lines = json.load(f)

    for line in text_lines:
        text = line.get("text", "").strip()
        if not text:
            continue
            
        x = line["x"]
        y_top = line["y_top"]
        # In the new structure, text_lines might have y_top and y_bot instead of height
        if "height" in line:
            height = line["height"]
        else:
            height = line["y_bot"] - line["y_top"]
            
        font_size = height
        
        # Adjust y to be the baseline
        y_baseline = y_top + height - (font_size * 0.15)
        
        text_elem = ET.Element("{http://www.w3.org/2000/svg}text")
        text_elem.set("x", str(x))
        text_elem.set("y", str(y_baseline))
        text_elem.set("font-family", "'Meiryo', 'Yu Gothic', sans-serif")
        text_elem.set("font-size", str(font_size))
        text_elem.set("fill", "#000000")
        text_elem.text = text
        
        root.append(text_elem)

    # Save the final SVG
    try:
        tree.write(args.output, encoding="utf-8", xml_declaration=True)
        print(f"[SUCCESS] Generated final SVG: {args.output}")
    except Exception as e:
        print(f"[ERROR] Failed to save final SVG: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
