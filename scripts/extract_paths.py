import os
import sys
import argparse
import tempfile
import subprocess
import json
import re
import xml.etree.ElementTree as ET
from PIL import Image, ImageMath

def binarize_image(image_path, grayscale_method, threshold, invert, binarize_min=None, binarize_max=None, val_inside=255, val_outside=0):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Input file not found: {image_path}")
    try:
        img = Image.open(image_path)
        img.load()
    except Exception as e:
        raise ValueError(f"Failed to load image: {e}")

    # Composite alpha channel onto white background
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        alpha = img.split()[-1]
        background.paste(img, mask=alpha)
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # Convert to grayscale
    r, g, b = img.split()
    if grayscale_method == 'luminosity':
        gray = img.convert('L')
    elif grayscale_method == 'average':
        gray = ImageMath.unsafe_eval("convert((r + g + b) / 3, 'L')", r=r, g=g, b=b)
    elif grayscale_method == 'lightness':
        max_img = ImageMath.unsafe_eval("max(r, max(g, b))", r=r, g=g, b=b)
        min_img = ImageMath.unsafe_eval("min(r, min(g, b))", r=r, g=g, b=b)
        gray = ImageMath.unsafe_eval("convert((max_img + min_img) / 2, 'L')", max_img=max_img, min_img=min_img)
    elif grayscale_method == 'r':
        gray = r
    elif grayscale_method == 'g':
        gray = g
    elif grayscale_method == 'b':
        gray = b
    elif grayscale_method in ('h', 's', 'v'):
        try:
            hsv = img.convert('HSV')
            h, s, v_chan = hsv.split()
            if grayscale_method == 'h':
                gray = h
            elif grayscale_method == 's':
                gray = s
            else:
                gray = v_chan
        except Exception as e:
            print(f"Warning: HSV conversion failed ({e}), falling back to average", file=sys.stderr)
            gray = ImageMath.unsafe_eval("convert((r + g + b) / 3, 'L')", r=r, g=g, b=b)
    else:
        raise ValueError(f"Unknown grayscale method: {grayscale_method}")

    # Apply binarization threshold
    if binarize_min is not None or binarize_max is not None:
        b_min = binarize_min if binarize_min is not None else 0
        b_max = binarize_max if binarize_max is not None else 255
        fn = lambda x: val_inside if (b_min <= x <= b_max) else val_outside
    else:
        if invert:
            fn = lambda x: 0 if x >= threshold else 255
        else:
            fn = lambda x: 255 if x >= threshold else 0

    monochrome = gray.point(fn, mode='1')
    return img, monochrome

def run_potrace(pbm_path, turdsize, alphamax, opttolerance):
    cmd = [
        "potrace",
        "--svg",
        "-o", "-",
        "--turdsize", str(turdsize),
        "--alphamax", str(alphamax),
        "--opttolerance", str(opttolerance),
        pbm_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return ET.fromstring(result.stdout)
    except FileNotFoundError:
        raise FileNotFoundError("Potrace is unavailable. Please install potrace and ensure it is in your PATH.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Potrace execution failed: {e.stderr}")
    except ET.ParseError as e:
        raise RuntimeError(f"Failed to parse Potrace SVG output: {e}")

def extract_paths_from_svg(svg_root):
    paths = []
    ns = {"svg": "http://www.w3.org/2000/svg"}
    
    g_elem = svg_root.find(".//svg:g", ns)
    if g_elem is None:
        g_elem = svg_root.find(".//g")
        
    trans_x, trans_y = 0.0, 0.0
    scale_x, scale_y = 1.0, 1.0
    
    if g_elem is not None and "transform" in g_elem.attrib:
        transform_str = g_elem.attrib["transform"]
        trans_match = re.search(r"translate\(([-+]?\d*\.?\d+),\s*([-+]?\d*\.?\d+)\)", transform_str)
        if trans_match:
            trans_x = float(trans_match.group(1))
            trans_y = float(trans_match.group(2))
            
        scale_match = re.search(r"scale\(([-+]?\d*\.?\d+),\s*([-+]?\d*\.?\d+)\)", transform_str)
        if scale_match:
            scale_x = float(scale_match.group(1))
            scale_y = float(scale_match.group(2))
            
    path_elems = svg_root.findall(".//svg:path", ns)
    if not path_elems:
        path_elems = svg_root.findall(".//path")
        
    for p in path_elems:
        d = p.attrib.get("d", "")
        if d:
            paths.append(d)
            
    return paths, trans_x, trans_y, scale_x, scale_y

def transform_and_measure_path(d_str, trans_x, trans_y, scale_x, scale_y):
    subpath_count = 0
    point_count = 0
    tokens = re.findall(r'([a-zA-Z])|([-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?)', d_str)
    
    current_x, current_y = 0.0, 0.0
    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')
    
    new_d = []
    i = 0
    while i < len(tokens):
        t_cmd, t_num = tokens[i]
        if t_cmd:
            command = t_cmd
            new_d.append(command)
            if command in ('M', 'm'): subpath_count += 1
            i += 1
            coords = []
            while i < len(tokens) and not tokens[i][0]:
                coords.append(float(tokens[i][1]))
                i += 1
            if not coords: continue
                
            is_relative = command.islower()
            cmd_upper = command.upper()
            if cmd_upper in ('M', 'L', 'T'): chunk_size = 2
            elif cmd_upper in ('H', 'V'): chunk_size = 1
            elif cmd_upper in ('S', 'Q'): chunk_size = 4
            elif cmd_upper in ('C',): chunk_size = 6
            elif cmd_upper in ('A',): chunk_size = 7
            else: chunk_size = 2
            
            idx = 0
            while idx < len(coords):
                chunk = coords[idx:idx+chunk_size]
                new_chunk = []
                
                if cmd_upper in ('M', 'L', 'T', 'C', 'S', 'Q'):
                    start_x, start_y = current_x, current_y
                    for j in range(0, len(chunk), 2):
                        x, y = chunk[j], chunk[j+1]
                        nx = x * scale_x
                        ny = y * scale_y
                        
                        if is_relative:
                            abs_x = start_x + nx
                            abs_y = start_y + ny
                        else:
                            nx += trans_x
                            ny += trans_y
                            abs_x = nx
                            abs_y = ny
                            
                        new_chunk.extend([nx, ny])
                        min_x = min(min_x, abs_x)
                        max_x = max(max_x, abs_x)
                        min_y = min(min_y, abs_y)
                        max_y = max(max_y, abs_y)
                        
                        if j == len(chunk) - 2:
                            current_x = abs_x
                            current_y = abs_y
                        
                    if cmd_upper in ('M', 'L', 'T'): point_count += 1
                    elif cmd_upper in ('S', 'Q'): point_count += 2
                    elif cmd_upper in ('C',): point_count += 3
                    
                elif cmd_upper == 'H':
                    x = chunk[0]
                    nx = x * scale_x
                    if is_relative:
                        abs_x = current_x + nx
                    else:
                        nx += trans_x
                        abs_x = nx
                        
                    new_chunk.append(nx)
                    current_x = abs_x
                    min_x = min(min_x, current_x)
                    max_x = max(max_x, current_x)
                    point_count += 1
                    
                elif cmd_upper == 'V':
                    y = chunk[0]
                    ny = y * scale_y
                    if is_relative:
                        abs_y = current_y + ny
                    else:
                        ny += trans_y
                        abs_y = ny
                        
                    new_chunk.append(ny)
                    current_y = abs_y
                    min_y = min(min_y, current_y)
                    max_y = max(max_y, current_y)
                    point_count += 1
                    
                elif cmd_upper == 'A':
                    rx, ry, rot, large, sweep, x, y = chunk
                    nrx = rx * abs(scale_x)
                    nry = ry * abs(scale_y)
                    if scale_x * scale_y < 0:
                        sweep = 1 - sweep
                        
                    nx = x * scale_x
                    ny = y * scale_y
                    if is_relative:
                        abs_x = current_x + nx
                        abs_y = current_y + ny
                    else:
                        nx += trans_x
                        ny += trans_y
                        abs_x = nx
                        abs_y = ny
                        
                    new_chunk = [nrx, nry, rot, large, sweep, nx, ny]
                    current_x = abs_x
                    current_y = abs_y
                    
                    min_x = min(min_x, current_x)
                    max_x = max(max_x, current_x)
                    min_y = min(min_y, current_y)
                    max_y = max(max_y, current_y)
                    point_count += 1
                    
                formatted = [f"{v:g}" if isinstance(v, int) or v.is_integer() else f"{v:.4f}" for v in new_chunk]
                new_d.append(" ".join(formatted))
                idx += chunk_size
                
                if command == 'M':
                    command, is_relative, cmd_upper = 'L', False, 'L'
                elif command == 'm':
                    command, is_relative, cmd_upper = 'l', True, 'L'
        else:
            i += 1
            
    if min_x == float('inf'):
        bbox = {"x": 0, "y": 0, "width": 0, "height": 0}
    else:
        bbox = {
            "x": round(min_x, 4),
            "y": round(min_y, 4),
            "width": round(max_x - min_x, 4),
            "height": round(max_y - min_y, 4)
        }
    return " ".join(new_d), subpath_count, point_count, bbox

def main():
    parser = argparse.ArgumentParser(description="Extract vector paths from raster images.")
    parser.add_argument("INPUT", help="Path to the input raster image")
    parser.add_argument("OUTPUT_DIRECTORY", help="Path to the output directory")
    parser.add_argument("--grayscale-method", choices=["average", "luminosity", "lightness", "r", "g", "b", "h", "s", "v"], default="average")
    parser.add_argument("--threshold", type=int, default=128)
    parser.add_argument("--invert", action="store_true")
    parser.add_argument("--binarize-min", type=int, default=None)
    parser.add_argument("--binarize-max", type=int, default=None)
    parser.add_argument("--value-inside", type=int, default=255)
    parser.add_argument("--value-outside", type=int, default=0)
    parser.add_argument("--turdsize", type=int, default=2)
    parser.add_argument("--alphamax", type=float, default=1.0)
    parser.add_argument("--opttolerance", type=float, default=0.2)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--prefix", type=str, default=None, help="Prefix for output files. If provided, disables auto-increment.")
    
    args = parser.parse_args()

    # Remove the existing state files at the start of processing
    for state_file in ["current_working_folder.txt", "param_extract_paths.txt"]:
        if os.path.exists(state_file):
            try:
                os.remove(state_file)
            except Exception as e:
                print(f"Warning: Failed to delete {state_file}: {e}", file=sys.stderr)

    # Auto-generate run folder if targeting the root "Outputs" directory
    out_dir_base = os.path.basename(os.path.normpath(args.OUTPUT_DIRECTORY))
    if out_dir_base.lower() == "outputs":
        import re
        base_name = os.path.splitext(os.path.basename(args.INPUT))[0]
        run_idx = 1
        os.makedirs(args.OUTPUT_DIRECTORY, exist_ok=True)
        for d in os.listdir(args.OUTPUT_DIRECTORY):
            if d.startswith(f"{base_name}_"):
                match = re.search(r'_(\d+)$', d)
                if match:
                    idx = int(match.group(1))
                    if idx >= run_idx:
                        run_idx = idx + 1
        args.OUTPUT_DIRECTORY = os.path.join(args.OUTPUT_DIRECTORY, f"{base_name}_{run_idx:03d}")

    if os.path.exists(args.OUTPUT_DIRECTORY) and not args.force:
        print(f"Error: Output directory already exists: {args.OUTPUT_DIRECTORY}\nUse --force to overwrite.", file=sys.stderr)
        sys.exit(1)

    try:
        orig_img, mono_img = binarize_image(
            args.INPUT,
            args.grayscale_method,
            args.threshold,
            args.invert,
            binarize_min=args.binarize_min,
            binarize_max=args.binarize_max,
            val_inside=args.value_inside,
            val_outside=args.value_outside
        )
    except Exception as e:
        print(f"Error processing image: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        with tempfile.NamedTemporaryFile(suffix=".pbm", delete=False) as temp_pbm:
            temp_pbm_path = temp_pbm.name
        mono_img.save(temp_pbm_path, format="PPM")
        
        # Invoke Potrace
        svg_root = run_potrace(temp_pbm_path, args.turdsize, args.alphamax, args.opttolerance)
        
        os.makedirs(args.OUTPUT_DIRECTORY, exist_ok=True)
        
        if args.prefix:
            v_str = args.prefix
            original_file = f"{args.prefix}_original.png"
            combined_file = f"{args.prefix}_combined.svg"
            metadata_file = f"{args.prefix}_metadata.json"
            svgs_folder = f"{args.prefix}_svgs"
        else:
            existing_combined = [f for f in os.listdir(args.OUTPUT_DIRECTORY) if f.startswith("combined") and f.endswith(".svg")]
            max_idx = 0
            import re
            for f in existing_combined:
                match = re.search(r"combined(\d+)\.svg", f)
                if match:
                    idx = int(match.group(1))
                    if idx > max_idx:
                        max_idx = idx
            v_str = f"{max_idx + 1:03d}"
            original_file = f"original{v_str}.png"
            combined_file = f"combined{v_str}.svg"
            metadata_file = f"metadata{v_str}.json"
            svgs_folder = f"svgs{v_str}"
        
        # Copy original
        original_copy_path = os.path.join(args.OUTPUT_DIRECTORY, original_file)
        orig_img.save(original_copy_path, format="PNG")
        
        # Create svgs folder
        svgs_dir = os.path.join(args.OUTPUT_DIRECTORY, svgs_folder)
        os.makedirs(svgs_dir, exist_ok=True)
        
        # Parse SVG and transform
        raw_paths, trans_x, trans_y, scale_x, scale_y = extract_paths_from_svg(svg_root)
        
        metadata = {
            "version": v_str,
            "source": os.path.basename(args.INPUT),
            "originalImage": original_file,
            "combinedSvg": combined_file,
            "width": orig_img.width,
            "height": orig_img.height,
            "parameters": {
                "grayscaleMethod": args.grayscale_method,
                "threshold": args.threshold,
                "invert": args.invert,
                "binarize_min": args.binarize_min,
                "binarize_max": args.binarize_max,
                "value_inside": args.value_inside,
                "value_outside": args.value_outside,
                "turdsize": args.turdsize,
                "alphamax": args.alphamax,
                "opttolerance": args.opttolerance
            },
            "pathCount": 0,
            "paths": []
        }
        
        # Generate combined SVG file and individual SVGs
        combined_svg_path = os.path.join(args.OUTPUT_DIRECTORY, combined_file)
        svg_paths = []
        
        for idx, d_str in enumerate(raw_paths, start=1):
            new_d, subpaths, points, bbox = transform_and_measure_path(d_str, trans_x, trans_y, scale_x, scale_y)
            path_id = f"path_{idx:03d}"
            path_element = f'  <path id="{path_id}" d="{new_d}" />'
            svg_paths.append(path_element)
            
            # Save individual SVG
            indiv_svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {orig_img.width} {orig_img.height}">\n{path_element}\n</svg>'
            with open(os.path.join(svgs_dir, f"{path_id}.svg"), "w", encoding="utf-8") as f:
                f.write(indiv_svg)
                
            metadata["paths"].append({
                "id": path_id,
                "file": f"{svgs_folder}/{path_id}.svg",
                "boundingBox": bbox,
                "subpathCount": subpaths,
                "pointCount": points,
                "accepted": None # Will be populated by AI agent
            })
            
        # Write combined SVG
        svg_content = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {orig_img.width} {orig_img.height}">\n'
        svg_content += "\n".join(svg_paths)
        svg_content += '\n</svg>'
        
        with open(combined_svg_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
            
        metadata["pathCount"] = len(raw_paths)
        with open(os.path.join(args.OUTPUT_DIRECTORY, metadata_file), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
            
        print(f"\n[SUCCESS] Saved all outputs to folder: {args.OUTPUT_DIRECTORY}")
        
        # Write to current_working_folder.txt in the root directory
        with open("current_working_folder.txt", "w", encoding="utf-8") as cwf:
            cwf.write(args.OUTPUT_DIRECTORY.replace("\\", "/"))
            
        # Write the binarization parameters to param_extract_paths.txt
        param_str = f"--grayscale-method {args.grayscale_method} --binarize-min {args.binarize_min} --binarize-max {args.binarize_max} --value-inside {args.value_inside} --value-outside {args.value_outside}"
        with open("param_extract_paths.txt", "w", encoding="utf-8") as p_file:
            p_file.write(param_str)
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error generating SVGs: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if 'temp_pbm_path' in locals() and os.path.exists(temp_pbm_path):
            os.remove(temp_pbm_path)

if __name__ == "__main__":
    main()
