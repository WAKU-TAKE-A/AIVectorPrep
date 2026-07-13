import json
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import sys

def build_parser():
    parser = argparse.ArgumentParser(description="JSONのBoundingBox座標を元に画像に枠と番号を描画する(Set-of-Mark OCR用)")
    parser.add_argument("-i", "--image", required=True, help="元画像のパス (例: Outputs/original001.png)")
    parser.add_argument("-j", "--json", required=True, help="text_lines JSONのパス (例: Outputs/text_lines001.json)")
    parser.add_argument("-o", "--output", help="出力画像パス (デフォルト: 元画像名の末尾に _roi を追加)")
    return parser

def main():
    args = build_parser().parse_args()

    img_path = Path(args.image)
    json_path = Path(args.json)

    if not img_path.exists():
        print(f"[ERROR] Image file not found: {img_path}", file=sys.stderr)
        sys.exit(1)
    if not json_path.exists():
        print(f"[ERROR] JSON file not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.output) if args.output else img_path.with_name(f"{img_path.stem}_text_roi{img_path.suffix}")

    # 画像をロード
    try:
        img = Image.open(img_path).convert("RGBA")
    except Exception as e:
        print(f"[ERROR] Failed to load image: {e}", file=sys.stderr)
        sys.exit(1)
        
    draw = ImageDraw.Draw(img)

    # フォントのロード
    try:
        font = ImageFont.truetype("arial.ttf", 10)
    except IOError:
        font = ImageFont.load_default()

    # JSONをロード
    with open(json_path, "r", encoding="utf-8") as f:
        lines = json.load(f)

    for line in lines:
        line_no = line["line_no"]
        x = line["x"]
        y_top = line["y_top"]
        x_right = line["x_right"]
        y_bot = line["y_bot"]

        # バウンディングボックスの描画（細い赤線）
        draw.rectangle([x, y_top, x_right, y_bot], outline="red", width=1)

        # ラベルテキストのサイズ取得
        label_text = str(line_no)
        if hasattr(font, 'getbbox'):
            bbox = font.getbbox(label_text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            text_width, text_height = draw.textsize(label_text, font=font)
            
        # ラベル背景の座標計算（ボックス外側左上）
        label_bg_coords = [
            x, 
            y_top - text_height - 4, 
            x + text_width + 4, 
            y_top
        ]
        
        # 画面上端にはみ出す場合はボックス内側へ
        if y_top - text_height - 4 < 0:
            label_bg_coords = [
                x, 
                y_top, 
                x + text_width + 4, 
                y_top + text_height + 4
            ]

        # ラベルの描画
        draw.rectangle(label_bg_coords, fill="red")
        draw.text((label_bg_coords[0] + 2, label_bg_coords[1] + 1), label_text, fill="white", font=font)

        # "text" キーが存在しない場合は空文字で初期化
        if "text" not in line:
            line["text"] = ""

    # 画像の保存
    img.save(out_path)
    print(f"Saved annotated image to {out_path}")

    # JSONの上書き保存（"text"キーの初期化を反映）
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(lines, f, indent=2, ensure_ascii=False)
    print(f"Updated {json_path} with empty 'text' keys if missing")

if __name__ == "__main__":
    main()
