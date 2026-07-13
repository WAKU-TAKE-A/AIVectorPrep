import argparse
import json
import os
import sys
from PIL import Image, ImageDraw

def main():
    parser = argparse.ArgumentParser(description="Erase text regions from an image based on OCR JSON.")
    parser.add_argument("-i", "--input", required=True, help="Input original image")
    parser.add_argument("-j", "--json", required=True, help="Input text lines JSON")
    parser.add_argument("-o", "--output", required=True, help="Output image path")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: {args.input} not found.", file=sys.stderr)
        sys.exit(1)
        
    if not os.path.exists(args.json):
        print(f"Error: {args.json} not found.", file=sys.stderr)
        sys.exit(1)

    img = Image.open(args.input).convert("RGB")
    draw = ImageDraw.Draw(img)
    
    with open(args.json, "r", encoding="utf-8") as f:
        lines = json.load(f)
        
    for line in lines:
        text = line.get("text", "")
        # Only erase if there's actual text (i.e. we didn't explicitly ignore it by leaving it blank)
        if text.strip() != "":
            x1 = line["x"]
            y1 = line["y_top"]
            x2 = line["x_right"]
            y2 = line["y_bot"]
            
            # Sample background color (slightly above/left of the box to get the page background)
            bg_x = max(0, x1 - 5)
            bg_y = max(0, y1 - 5)
            bg_color = img.getpixel((bg_x, bg_y))
            
            # Fill the bounding box with the sampled background color
            draw.rectangle([x1, y1, x2, y2], fill=bg_color)
            
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    img.save(args.output)
    print(f"[SUCCESS] Saved text-erased image: {args.output}")

if __name__ == "__main__":
    main()
