import os
import json
import argparse
from PIL import Image

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", required=True, help="Path to config JSON")
    parser.add_argument("-s", "--source", help="Override source image path from JSON")
    parser.add_argument("-d", "--dest", help="Override destination directory from JSON")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        config = json.load(f)

    # Use args if provided, else fallback to JSON
    source_img_path = args.source if args.source else config["source_image"]
    dest_dir = args.dest if args.dest else config["dest_dir"]

    src_img = Image.open(source_img_path)
    os.makedirs(dest_dir, exist_ok=True)

    print(f"Loaded source image: {source_img_path} ({src_img.width}x{src_img.height})")
    for idx, reg in enumerate(config["regions"], 1):
        label = reg["label"]
        bbox = reg["bbox"] # [x, y, w, h]
        x, y, w, h = bbox
        
        # クロップ
        cropped = src_img.crop((x, y, x + w, y + h))
        
        # 保存

        out_path = os.path.join(dest_dir, f"{label}.png")
        cropped.save(out_path, format="PNG")
        print(f"  [{idx}/{len(config['regions'])}] Saved: {out_path} ({w}x{h})")
    print("Crop processing completed successfully.")

if __name__ == "__main__":
    main()
