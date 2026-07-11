# AI Vector SVG Preparation - AI向け開発規約 & 運用ルール (README_AI.md)

このドキュメントは、本リポジトリにおける画像処理およびSVG再構築パイプラインの運用と、AIエージェントによるファイル操作・スクリプト管理の共通ルールを定めたものです。

---

## 1. プロジェクト構造とスクリプト管理

リポジトリルートをクリーンに保つため、スクリプトは以下の分類に従って厳格に管理します。

### A. 汎用・システムスクリプト (リポジトリルートに配置)
- 主要なパイプライン処理を行う、高い汎用性を持ったプロダクションコードです。
- 例: `extract_paths.py` (画像の前処理・二値化・Potraceによるパス抽出・実座標計測を担うコアツール)

### B. 一時スクリプト・検証用コード (必ず `temp_scripts/` に配置)
- 特定のタスク、検証、または1回限りのデータ操作（カラーサンプリング、SVGの一時結合など）のために作成されたスクリプトです。
- **配置ルール**:
  - ルートディレクトリには絶対に直接配置せず、必ず [temp_scripts/](file:///c:/UserData/nishida/Git/AIVectorPrep/temp_scripts/) ディレクトリ配下に作成してください。
- **実行回数記録ルール**:
  - すべての一時スクリプトの**先頭行（1行目）**には、必ずそのスクリプトを実行した累計回数をコメント行として記述します。
    ```python
    # Run count: 1
    ```
  - AIエージェントが既存の一時スクリプトを実行する際は、**必ずこの先頭行の数値をインクリメント（+1）して上書き保存した後に実行**してください。
- **汎用スクリプトへの昇進**:
  - 複数回実行され、今後の汎用的なユーティリティとしての利用価値が高いと判断されたスクリプトは、リファクタリングを行った上でルートディレクトリに「昇進（配置）」させることができます。

---

## 2. コアツール紹介

### [extract_paths.py](file:///c:/UserData/nishida/Git/AIVectorPrep/extract_paths.py) (汎用)
画像からベクターパスを抽出するメインエンジンです。
- **主なオプション**:
  - `--grayscale-method`: グレースケール変換方法の指定（`luminosity`, `average`, `lightness`, `r`, `g`, `b`, `h`, `s`, `v`）
  - `--binarize-min` / `--binarize-max`: 範囲指定による二値化しきい値
  - `--value-inside` / `--value-outside`: 範囲内・範囲外の置き換え値（デフォルト: 内側が0、外側が255）
  - `--turdsize`: ノイズ除去サイズ（Potraceに渡すパラメータ）

### [analyze_text_regions.py](file:///c:/UserData/nishida/Git/AIVectorPrep/analyze_text_regions.py) (汎用)
`extract_paths.py` が出力した `metadata*.json` を解析し、テキスト行のバウンディングボックスを実測値で抽出する汎用 CLI です。
- **主なオプション**:
  - `-m / --metadata`: 入力 metadata JSON（必須）
  - `-o / --output`: 出力 JSON パス（省略時は自動命名）
  - `--area-max / --area-min`: グリフとみなす bbox 面積の上下限（省略時は画像サイズから自動計算）
  - `--dim-max`: グリフとみなす bbox 最大辺長（省略時は自動計算）
  - `--line-tol`: 行クラスタリングの y 方向許容幅（省略時は自動計算）
  - `--min-paths`: 1行とみなす最小パス数（デフォルト: 3）
  - `--scale`: 自動計算される全閾値を一括スケーリング（デフォルト: 1.0）
  - `-v / --verbose`: 詳細ログ出力

---

## 3. 現在の一時スクリプト一覧 (`temp_scripts/` 配下)

- **[temp_scripts/extract_colors.py](file:///c:/UserData/nishida/Git/AIVectorPrep/temp_scripts/extract_colors.py)** (`# Run count: 1`)
  - 元画像から文字領域を除外した上で、採用されたイラストパスの領域色をサンプリングするカラー抽出スクリプト。
- **[temp_scripts/compose_final_svg.py](file:///c:/UserData/nishida/Git/AIVectorPrep/temp_scripts/compose_final_svg.py)** (`# Run count: 3`)
  - 評価済みメタデータと個別SVGから最終的な統合SVGを構築する初期試作スクリプト。
- **[temp_scripts/test_svg_parser.py](file:///c:/UserData/nishida/Git/AIVectorPrep/temp_scripts/test_svg_parser.py)** (`# Run count: 2`)
  - SVGパスのパース処理とアフィン行列計算の精度をチェックするための単体テスト用スクリプト。
- **[temp_scripts/analyze_text_regions.py](file:///c:/UserData/nishida/Git/AIVectorPrep/temp_scripts/analyze_text_regions.py)** (`# Run count: 1`)
  - 旧版（固定閾値）。ルートの汎用版 `analyze_text_regions.py` に昇進済み。参照のみ。
- **[temp_scripts/crop_and_embed.py](file:///c:/UserData/nishida/Git/AIVectorPrep/temp_scripts/crop_and_embed.py)** (`# Run count: 3`)
  - `original002.png` からイラスト領域をクロップし、base64 で `text002.svg` に埋め込む。
- **[temp_scripts/embed_into_text003.py](file:///c:/UserData/nishida/Git/AIVectorPrep/temp_scripts/embed_into_text003.py)** (`# Run count: 2`)
  - 既存クロップ画像を `text003.svg` に埋め込む。
