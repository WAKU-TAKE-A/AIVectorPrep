import json
import argparse
from pathlib import Path
import sys

def build_parser():
    parser = argparse.ArgumentParser(description="AI OCRの結果が記載された辞書JSONを読み込み、元の text_lines JSON の text キーを更新する")
    parser.add_argument("-j", "--json", required=True, help="更新対象の text_lines JSON パス (例: Outputs/text_lines001.json)")
    parser.add_argument("-d", "--data", required=True, help="OCR結果の辞書データ JSON パス (例: temp_scripts/ocr001.json)")
    return parser

def main():
    args = build_parser().parse_args()

    target_json_path = Path(args.json)
    data_json_path = Path(args.data)

    if not target_json_path.exists():
        print(f"[ERROR] Target JSON file not found: {target_json_path}", file=sys.stderr)
        sys.exit(1)
        
    if not data_json_path.exists():
        print(f"[ERROR] Data JSON file not found: {data_json_path}", file=sys.stderr)
        sys.exit(1)

    # データの読み込み
    with open(target_json_path, "r", encoding="utf-8") as f:
        target_data = json.load(f)
        
    with open(data_json_path, "r", encoding="utf-8") as f:
        ocr_results = json.load(f)
        
    # キーが文字列で読み込まれるため、整数に変換可能なものは変換する
    ocr_dict = {}
    for k, v in ocr_results.items():
        try:
            ocr_dict[int(k)] = v
        except ValueError:
            ocr_dict[k] = v

    # テキストの更新
    updated_count = 0
    for line in target_data:
        line_no = line["line_no"]
        if line_no in ocr_dict:
            line["text"] = ocr_dict[line_no]
            updated_count += 1

    # 上書き保存
    with open(target_json_path, "w", encoding="utf-8") as f:
        json.dump(target_data, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully updated {updated_count} text regions in {target_json_path}")

if __name__ == "__main__":
    main()
