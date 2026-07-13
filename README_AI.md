# AI Vector SVG Preparation - AI向け開発規約 & 運用ルール (README_AI.md)

このドキュメントは、本リポジトリにおける画像処理およびSVG再構築パイプラインの運用と、AIエージェントによるファイル操作・スクリプト管理 of 共通ルールを定めたものです。

---

## 1. プロジェクト構造とスクリプト管理

リポジトリルートをクリーンに保つため、スクリプトは以下の分類に従って厳格に管理します。

### A. 汎用・システムスクリプト (必ず `scripts/` に配置)
- 主要なパイプライン処理を行う、高い汎用性を持ったプロダクションコードです。
- 例: `scripts/extract_paths.py` (画像の前処理・二値化・Potraceによるパス抽出・実座標計測を担うコアツール)

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

---

## 2. コアツール紹介

### [scripts/extract_paths.py](file:///c:/UserData/nishida/Git/AIVectorPrep/scripts/extract_paths.py) (汎用)
画像からベクターパスを抽出するメインエンジンです。

### [scripts/analyze_text_regions.py](file:///c:/UserData/nishida/Git/AIVectorPrep/scripts/analyze_text_regions.py) (汎用)
`extract_paths.py` が出力した `metadata*.json` を解析し、テキスト行のバウンディングボックスを実測値で抽出する汎用 CLI です。

### [scripts/auto_cluster.py](file:///c:/UserData/nishida/Git/AIVectorPrep/scripts/auto_cluster.py) (汎用)
抽出されたSVGパス同士の「面積の重なり判定」を全BBoxに対して行い、自動的に部品（コンポーネント）単位の矩形にクラスタリングして `crop_config.json` を出力する自動グルーピングツールです。手動でのアタリ矩形指定を不要にします。

### [scripts/draw_text_roi.py](file:///c:/UserData/nishida/Git/AIVectorPrep/scripts/draw_text_roi.py) (汎用)
`text_lines*.json` のバウンディングボックス座標を元に、画像に極小の番号ラベルと枠線を描画し、AI向けの「Set-of-Mark OCR用ナビゲーション画像」を生成するツールです。

### [scripts/update_text_lines.py](file:///c:/UserData/nishida/Git/AIVectorPrep/scripts/update_text_lines.py) (汎用)
AIがOCRした結果（`{"1": "テキスト", "2": ""}` のような辞書データJSON）を読み込み、元の `text_lines*.json` の `text` キーを一括で上書き更新するツールです。

### [scripts/erase_text_regions.py](file:///c:/UserData/nishida/Git/AIVectorPrep/scripts/erase_text_regions.py) (汎用)
`text_lines*.json` に基づき、文字が存在する領域を画像から背景色で塗りつぶし、「文字なし背景画像」を生成するツールです。

### [scripts/crop_illustrations.py](file:///c:/UserData/nishida/Git/AIVectorPrep/scripts/crop_illustrations.py) (汎用)
`crop_config.json` に基づき、文字なし画像からイラスト部品単位の純粋なPNG画像を切り出して出力するツールです。コマンドライン引数で入力画像や出力先をオーバーライドできます。

### [scripts/build_final_svg.py](file:///c:/UserData/nishida/Git/AIVectorPrep/scripts/build_final_svg.py) (汎用)
ベースとなるSVG（文字抜き）に、切り出したPNGパーツ群を `<image>` タグ（Base64埋め込み）で配置し、さらにOCRで読み取ったテキストを `<text>` タグで正確な座標にオーバーレイして、完全なハイブリッドSVGを生成する最終ビルドツールです。

---

## 3. フォルダ構造・ファイル命名規則（標準化パイプライン）

1回の画像処理タスクごとに、出力先として専用のディレクトリ `Outputs/[拡張子無しファイル名]_XXX/`（例: `Outputs/demo006_001/`）を作成し、すべての成果物をその中に格納します。ファイル名にはステップ番号（`01`〜`07`）を含め、データフローを明確にします。

---

## 4. ハイブリッド・パイプライン標準ワークフロー

AIエージェントが画像を処理する際は、**必ず `step_executor.py` を用いて、ステップごとに指示を仰ぎながら**実行します。このスクリプトが「絶対のルールブック」です。

基本的な流れは以下の全8ステップです（詳細は `python scripts/step_executor.py [1-8] current_working_folder.txt` で確認すること）：

* **Step 1**: 初回パス抽出 (ベクター変換、メタデータ生成)
* **Step 2**: テキスト領域抽出 (BBox生成とナビゲーション画像出力)
* **Step 3**: AIによるOCRと自己補正（ハイブリッド処理のコア。アイコンやロゴは絶対に読まない！）
* **Step 4**: 文字領域を背景色で塗り消去
* **Step 5**: 文字領域の無い画像からパス抽出 (純粋なイラストパーツの取得)
* **Step 6**: 部品クラスタリング (コンポーネント単位のBBox生成)
* **Step 7**: イラスト画像の切り出し (ラスターベースでのCrop。**【黄金律】人物やアイコンを無理にベクターパスで表現してはいけない！**)
* **Step 8**: 統合SVGのビルド (PNG画像とテキストをSVGとして再構築)

AIはステップ完了ごとに `python scripts/step_executor.py [次のステップ番号] current_working_folder.txt` を実行し、指示に従って作業を進めてください。
マジックナンバー（例: `Outputs/demo006_001`）をAIが推測して埋め込むことは禁止です。必ず `current_working_folder.txt` を引数として渡し、動的に対象ディレクトリを決定してください。

---

## 5. AI向け開発黄金律 (Golden Rules)

AIエージェントが開発を行う際、以下の規約を絶対に遵守しなければなりません。破った場合は設計違反とみなされます。

### 黄金律1: イラストのパス代替禁止 (生成AIハイブリッド)
人物やアイコンなどのイラストパーツを Potrace 等のベクターパスで直接描画することは絶対にあり得ません。ベクターパスは吹き出し枠や矢印・星などの図形にのみ適用し、イラストは必ず元画像から正確にクロップした `<image>` を埋め込んで重ねること。

### 黄金律2: 座標の手動でっち上げ・調整禁止 (地図の絶対性)
AIエージェントが `crop_config.json` 内の `bbox` 座標を目分量で計算したり、勝手に調整（マージン加算、縮小など）することを厳禁とします。必ず `generate_crop_config.py` を実行して、地図（`metadata.json`）の物理限界数値をそのまま100%忠実に自動フィッティングさせること。

### 黄金律3: xlink:href 属性の必須化 (画像表示バグの防止)
生成するSVG内のすべての `<image>` タグには、必ず `href` 属性と `xlink:href` 属性の両方を設定すること。設定しない場合、ブラウザ等で画像が非表示になる重大な描画バグが発生します。
