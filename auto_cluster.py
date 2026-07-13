import os
import sys
import json
import argparse
from PIL import Image, ImageDraw

def boxes_should_merge(b1, b2, margin, threshold):
    x1, y1, w1, h1 = b1
    x2, y2, w2, h2 = b2
    
    area1 = w1 * h1
    area2 = w2 * h2
    if area1 == 0 or area2 == 0: return False
    
    ex1, ey1 = x1 - margin, y1 - margin
    ew1, eh1 = w1 + 2*margin, h1 + 2*margin
    ex2, ey2 = x2 - margin, y2 - margin
    ew2, eh2 = w2 + 2*margin, h2 + 2*margin
    
    ix_min = max(ex1, ex2)
    iy_min = max(ey1, ey2)
    ix_max = min(ex1 + ew1, ex2 + ew2)
    iy_max = min(ey1 + eh1, ey2 + eh2)
    
    if ix_max <= ix_min or iy_max <= iy_min:
        return False
        
    intersection_area = (ix_max - ix_min) * (iy_max - iy_min)
    
    if area1 > area2:
        return (intersection_area / area2) >= threshold
    else:
        return (intersection_area / area1) >= threshold

def get_merged_box(b1, b2):
    x1, y1, w1, h1 = b1
    x2, y2, w2, h2 = b2
    min_x = min(x1, x2)
    min_y = min(y1, y2)
    max_x = max(x1 + w1, x2 + w2)
    max_y = max(y1 + h1, y2 + h2)
    return [min_x, min_y, max_x - min_x, max_y - min_y]

def main():
    parser = argparse.ArgumentParser(description="Auto-cluster SVG paths into semantic components based on overlap and margin.")
    parser.add_argument("-m", "--metadata", required=True, help="Path to input metadata.json")
    parser.add_argument("-o", "--output", required=True, help="Path to output crop_config.json")
    parser.add_argument("-v", "--visualize", help="Path to save visualization image (optional)")
    parser.add_argument("--margin", type=int, default=5, help="Margin to expand boxes before overlap check (default: 5)")
    parser.add_argument("--threshold", type=float, default=0.2, help="Overlap ratio threshold (default: 0.2)")
    args = parser.parse_args()

    if not os.path.exists(args.metadata):
        print(f"Error: Metadata file not found: {args.metadata}", file=sys.stderr)
        sys.exit(1)

    with open(args.metadata, encoding="utf-8") as f:
        metadata = json.load(f)
        
    bboxes = []
    # Filter out ridiculously huge paths (slide background) and noise
    for p in metadata.get("paths", []):
        b = p["boundingBox"]
        if b["width"] > 1400 or b["height"] > 900: continue
        if b["width"] < 10 or b["height"] < 10: continue
        bboxes.append([b["x"], b["y"], b["width"], b["height"]])
        
    clusters = list(bboxes)
    
    while True:
        merged = False
        new_clusters = []
        skip_indices = set()
        
        for i in range(len(clusters)):
            if i in skip_indices: continue
            
            merged_box = clusters[i]
            for j in range(i + 1, len(clusters)):
                if j in skip_indices: continue
                if boxes_should_merge(merged_box, clusters[j], args.margin, args.threshold):
                    merged_box = get_merged_box(merged_box, clusters[j])
                    skip_indices.add(j)
                    merged = True
                    
            new_clusters.append(merged_box)
            
        clusters = new_clusters
        if not merged:
            break
            
    print(f"Auto-clustering completed: Generated {len(clusters)} regions.")

    # Generate regions for crop_config
    regions = []
    for idx, c in enumerate(clusters, start=1):
        x, y, w, h = c
        regions.append({
            "label": f"component_{idx:03d}",
            "bbox": [int(x), int(y), int(w), int(h)]
        })

    # The crop config needs a source image and dest dir to be valid for crop_illustrations.py.
    # We can infer source image from metadata, or just set it relative to the output config.
    source_img = metadata.get("originalImage", "")
    dest_dir = os.path.join(os.path.dirname(args.output), "crops_" + os.path.splitext(os.path.basename(args.output))[0])
    
    crop_config = {
        "source_image": os.path.join(os.path.dirname(args.metadata), source_img) if source_img else "",
        "dest_dir": dest_dir,
        "regions": regions
    }
    
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(crop_config, f, indent=2, ensure_ascii=False)
        
    # Visualize if requested
    if args.visualize:
        img_path = os.path.join(os.path.dirname(args.metadata), source_img)
        if os.path.exists(img_path):
            img = Image.open(img_path).convert("RGB")
            draw = ImageDraw.Draw(img)
            
            # Draw original paths faintly
            for b in bboxes:
                x, y, w, h = b
                draw.rectangle([x, y, x+w, y+h], outline=(200, 200, 255), width=1)
                
            # Draw clusters in thick red
            for b in clusters:
                x, y, w, h = b
                draw.rectangle([x, y, x+w, y+h], outline=(255, 0, 0), width=3)
                
            img.save(args.visualize)
            print(f"Saved visualization to {args.visualize}")
        else:
            print(f"Warning: Source image {img_path} not found. Skipping visualization.", file=sys.stderr)

if __name__ == "__main__":
    main()
