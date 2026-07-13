#!/usr/bin/env python3
"""
analyze_text_regions.py  ―  汎用テキスト行検出 CLI
=====================================================
Potrace パイプライン (extract_paths.py) が出力した metadata*.json を読み込み、
パスの bbox サイズ・密度に基づいてテキスト領域と行座標を自動検出する。

Usage
-----
    python analyze_text_regions.py -m Outputs/metadata002.json
    python analyze_text_regions.py -m Outputs/metadata002.json -o Outputs/text_lines002.json
    python analyze_text_regions.py -m Outputs/metadata002.json --dim-max 200 --line-tol 30 -v

Threshold defaults (image-size relative)
-----------------------------------------
  --area-max   : (short_side * 0.052) ** 2   ~ グリフ 1 文字の最大面積
  --area-min   : 30                           ~ ノイズ除去用下限
  --dim-max    : short_side * 0.10            ~ グリフ 1 文字の最大辺長
  --line-tol   : short_side * 0.016           ~ 行クラスタリング y 許容幅
  --min-paths  : 3                            ~ ノイズ行の除外閾値

全閾値を相対値で計算するため、解像度・フォントサイズが異なる画像でも
最小限のパラメータ調整で動作します。
"""

import argparse
import json
import math
import sys
from pathlib import Path


# ─────────────────────────────────────────────
# 引数パーサー
# ─────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="analyze_text_regions",
        description="metadata*.json からテキスト行の bbox を実測値で抽出する汎用 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "-m", "--metadata", required=True,
        help="extract_paths.py が出力した metadata*.json のパス",
    )
    p.add_argument(
        "-o", "--output", default=None,
        help="出力 JSON のパス (省略時: <metadata_stem>_text_lines.json)",
    )

    # ─── 閾値グループ ───
    thr = p.add_argument_group("閾値オプション (未指定時は画像サイズから自動計算)")
    thr.add_argument(
        "--area-max", type=float, default=None,
        metavar="PX2",
        help="グリフとみなす bbox 面積の上限 [px^2]  (default: (short_side*0.06)^2)",
    )
    thr.add_argument(
        "--area-min", type=float, default=30.0,
        metavar="PX2",
        help="ノイズ除去用 bbox 面積の下限 [px^2]  (default: 30)",
    )
    thr.add_argument(
        "--dim-max", type=float, default=None,
        metavar="PX",
        help="グリフとみなす bbox 最大辺長 [px]  (default: short_side*0.10)",
    )
    thr.add_argument(
        "--line-tol", type=float, default=None,
        metavar="PX",
        help="行クラスタリングの y 方向許容幅 [px]  (default: short_side*0.016)",
    )
    thr.add_argument(
        "--char-gap", type=float, default=None,
        metavar="PX",
        help="同じ行内で別ブロックとみなす X 方向の隙間 [px]  (default: short_side*0.04)",
    )
    thr.add_argument(
        "--min-paths", type=int, default=3,
        metavar="N",
        help="1 行とみなすのに必要な最小パス数  (default: 3)",
    )
    thr.add_argument(
        "--scale", type=float, default=1.0,
        metavar="FACTOR",
        help="自動計算される閾値をまとめてスケーリング  (default: 1.0)",
    )

    p.add_argument("-v", "--verbose", action="store_true",
                   help="詳細ログを出力する")
    return p


# ─────────────────────────────────────────────
# コア処理
# ─────────────────────────────────────────────
def load_metadata(path: Path) -> tuple[list, int, int]:
    with open(path, encoding="utf-8") as f:
        meta = json.load(f)
    return meta["paths"], meta["width"], meta["height"]


def compute_thresholds(W: int, H: int, args) -> dict:
    short = min(W, H)
    scale = args.scale

    area_max = args.area_max if args.area_max is not None \
        else (short * 0.06 * scale) ** 2
    area_min = args.area_min
    dim_max  = args.dim_max  if args.dim_max  is not None \
        else short * 0.10 * scale
    line_tol = args.line_tol if args.line_tol is not None \
        else short * 0.016 * scale
    char_gap = args.char_gap if args.char_gap is not None \
        else short * 0.04 * scale

    return dict(
        area_max=area_max,
        area_min=area_min,
        dim_max=dim_max,
        line_tol=line_tol,
        char_gap=char_gap,
        min_paths=args.min_paths,
    )


def classify_paths(paths: list, thr: dict) -> tuple[list, list]:
    text_candidates, illus_paths = [], []
    for p in paths:
        bb = p["boundingBox"]
        area   = bb["width"] * bb["height"]
        maxdim = max(bb["width"], bb["height"])
        p["_area"]   = area
        p["_maxdim"] = maxdim
        p["_cx"]     = bb["x"] + bb["width"]  / 2
        p["_cy"]     = bb["y"] + bb["height"] / 2

        if thr["area_min"] <= area <= thr["area_max"] and maxdim <= thr["dim_max"]:
            text_candidates.append(p)
        else:
            illus_paths.append(p)
    return text_candidates, illus_paths


def cluster_lines(text_candidates: list, line_tol: float) -> list:
    """y 中心でクラスタリングして「行」リストを返す。"""
    text_candidates.sort(key=lambda p: p["_cy"])
    lines = []
    for p in text_candidates:
        cy = p["_cy"]
        matched = False
        for line in lines:
            if abs(line["cy_mean"] - cy) <= line_tol:
                line["paths"].append(p)
                line["cy_mean"] = sum(q["_cy"] for q in line["paths"]) / len(line["paths"])
                matched = True
                break
        if not matched:
            lines.append({"cy_mean": cy, "paths": [p]})
    return lines


def split_lines_horizontally(lines: list, char_gap: float) -> list:
    """Y座標でまとまった行を、X座標の大きな隙間でさらに分割する。"""
    split_lines = []
    for line in lines:
        paths = line["paths"]
        # パスをX座標順にソート
        paths.sort(key=lambda p: p["boundingBox"]["x"])
        
        current_block_paths = []
        current_right = -float('inf')
        
        for p in paths:
            bb = p["boundingBox"]
            x_left = bb["x"]
            
            if not current_block_paths or (x_left - current_right) <= char_gap:
                current_block_paths.append(p)
                current_right = max(current_right, x_left + bb["width"])
            else:
                split_lines.append({"cy_mean": line["cy_mean"], "paths": current_block_paths})
                current_block_paths = [p]
                current_right = x_left + bb["width"]
                
        if current_block_paths:
            split_lines.append({"cy_mean": line["cy_mean"], "paths": current_block_paths})
            
    return split_lines

def aggregate_lines(lines: list, min_paths: int) -> list:
    """各行の集約 bbox を計算して返す。"""
    result = []
    for line in lines:
        ps = line["paths"]
        if len(ps) < min_paths:
            continue
        x_left  = min(p["boundingBox"]["x"] for p in ps)
        y_top   = min(p["boundingBox"]["y"] for p in ps)
        x_right = max(p["boundingBox"]["x"] + p["boundingBox"]["width"]  for p in ps)
        y_bot   = max(p["boundingBox"]["y"] + p["boundingBox"]["height"] for p in ps)
        result.append({
            "line_no":    len(result) + 1,
            "x":          round(x_left),
            "y_top":      round(y_top),
            "y_bot":      round(y_bot),
            "y_center":   round((y_top + y_bot) / 2),
            "x_right":    round(x_right),
            "width":      round(x_right - x_left),
            "height":     round(y_bot - y_top),
            "path_count": len(ps),
            "cy_mean":    line["cy_mean"],
        })
    return result


# ─────────────────────────────────────────────
# エントリポイント
# ─────────────────────────────────────────────
def main():
    args = build_parser().parse_args()

    meta_path = Path(args.metadata)
    if not meta_path.exists():
        print(f"[ERROR] metadata file not found: {meta_path}", file=sys.stderr)
        sys.exit(1)

    # 出力パスの決定
    out_path = Path(args.output) if args.output else \
        meta_path.parent / (meta_path.stem.replace("metadata", "text_lines") + ".json")

    # ── データ読み込み ──
    paths, W, H = load_metadata(meta_path)
    print(f"Image: {W}x{H}  |  total paths: {len(paths)}")

    # ── 閾値の計算 ──
    thr = compute_thresholds(W, H, args)
    if args.verbose:
        print("\n--- 使用閾値 ---")
        for k, v in thr.items():
            print(f"  {k:<12}: {v:.1f}" if isinstance(v, float) else f"  {k:<12}: {v}")

    # ── 分類 ──
    text_cands, illus = classify_paths(paths, thr)
    print(f"\nテキスト候補パス: {len(text_cands)}  |  イラスト系パス: {len(illus)}")

    # ── 行クラスタリング ──
    raw_lines   = cluster_lines(text_cands, thr["line_tol"])
    split_lines = split_lines_horizontally(raw_lines, thr["char_gap"])
    text_lines  = aggregate_lines(split_lines, thr["min_paths"])

    # ── 結果表示 ──
    print(f"\n{'行':>3}  {'y_top':>6} {'y_bot':>6} {'x_left':>7} {'x_right':>8} "
          f"{'paths':>6}  {'height':>6}")
    print("-" * 56)
    for ln in text_lines:
        print(f"{ln['line_no']:>3}  {ln['y_top']:>6} {ln['y_bot']:>6} "
              f"{ln['x']:>7} {ln['x_right']:>8} "
              f"{ln['path_count']:>6}  {ln['height']:>6}")

    print(f"\n合計 {len(text_lines)} 行を検出")

    # ── 境界サマリー（クロップ設計に使いやすい形式）──
    if text_lines:
        # 「全幅に近い行」= 本文テキストエリアの目安
        full_width = W
        wide_lines = [ln for ln in text_lines if ln["width"] > full_width * 0.7]
        if wide_lines:
            first_wide_y_top = wide_lines[0]["y_top"]
            print(f"\n[クロップ設計のヒント]")
            print(f"  全幅テキスト行の最初の y_top = {first_wide_y_top}")
            print(f"  → イラストクロップの下端は y ≦ {first_wide_y_top - 7} を推奨")

    # ── JSON 保存 ──
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(text_lines, f, indent=2, ensure_ascii=False)
    print(f"\n保存: {out_path}")


if __name__ == "__main__":
    main()
