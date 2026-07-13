import sys
import argparse
import os

def get_step_instructions(step):
    target_dir = "[作業フォルダ]"
    if os.path.exists("current_working_folder.txt"):
        with open("current_working_folder.txt", "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                # Ensure we display forward slashes
                target_dir = content.replace("\\", "/")

    params_A = "128"
    params_B = "255"
    params_C = "255"
    params_D = "0"
    params_str = f"--grayscale-method average --binarize-min {params_A} --binarize-max {params_B} --value-inside {params_C} --value-outside {params_D}"
    
    if os.path.exists("param_extract_paths.txt"):
        with open("param_extract_paths.txt", "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                params_str = content

    steps = {
        1: f"""
========================================================================
【Step 1】 パス抽出（ベクター変換）
========================================================================
[目的]
元画像からベクターパスを抽出し、メタデータとSVGを生成する。

[AIへの実行手順]
1. 必ず「--prefix 01_raw」
2. ユーザーから画像が指定されていること。
3. 抽出方法（--grayscale-method）、2値化の設定値（--binarize-min、--binarize-max、--value-inside）が設定されなかった場合、AIが設定した値をユーザーに伝えること。
4. 問題なければ、以下を実行すること。
   python extract_paths.py Inputs/[拡張子無し画像ファイル名].[jpg、pngなどの拡張子] Outputs --prefix 01_raw --grayscale-method average --binarize-min 128 --binarize-max 255 --value-inside 255 --value-outside 0
5. param_extract_paths.txtが生成されていることを確認する。
6. current_working_folder.txtが生成されていることを確認し、読み取り、作業フォルダを確認すること。
7. 作業フォルダに以下のファイルが出力されていることを確認する。
  - 01_raw_metadata.json （各パスのバウンディングボックスや色の情報を持つJSONファイル）
  - 01_raw_combined.svg （抽出された全パスをまとめた単一のSVGファイル）
  - 01_raw_svgs/ （個別のパスがそれぞれ1つずつ保存されたフォルダ）
  - 01_raw_original.png （元画像のコピー）
8. すべて問題なければ、`python step_executor.py 2` を実行すること。

[AIへの注意点]
- 問題がある場合は、停止。
""",
        2: f"""
========================================================================
【Step 2】 テキスト領域抽出
========================================================================
[目的]
抽出されたパスのメタデータから、テキスト（文字）と思われる領域のバウンディングボックスを特定する。

[AIへの実行手順]
1. current_working_folder.txtを読み取り、作業フォルダを確認すること。
2. 作業フォルダに01_raw_metadata.json、01_raw_original.pngがあることを確認すること。
3. 問題なければ、以下を実行する。
   python analyze_text_regions.py -m {target_dir}/01_raw_metadata.json -o {target_dir}/02_text_lines.json
4. 作業フォルダに02_text_lines.jsonが作成されたことを確認する。
5. 問題なければ、以下を実行する。
   python draw_text_roi.py -i {target_dir}/01_raw_original.png -j {target_dir}/02_text_lines.json -o {target_dir}/02_text_roi.png
6. 作業フォルダに02_text_roi.pngがあることを確認する。
7. すべて問題なければ、`python step_executor.py 3` を実行すること。

[AIへの注意点]
- 問題がある場合は、停止。
""",
        3: f"""
========================================================================
【Step 3】 AIによるOCRと自己補正（ハイブリッド処理のコア）
========================================================================
[目的]
AI自身が画像を見て、文字を読み取りJSONを更新する。

[AIの実行手順]
1. current_working_folder.txtを読み取り、作業フォルダを確認すること。
2. 作業フォルダに02_text_roi.pngがあることを確認する。
3. 問題なければ、AI（あなた）はview_fileツールを使って、作業フォルダ内の02_text_roi.pngを直接目視確認する。
4. OCRの実行と辞書JSONの作成:
   各番号に対する文字を読み取る。
   【重要】アイコンの誤検知や、ラスタライズしたまま残すべきロゴ（背景色に対し白抜きの文字の場合、明らかに矩形のサイズが文字列より小さい場合など）は絶対に無理に読まず、必ず空文字 "" にすること！
   結果を temp_scripts/ocr.json に保存する。
5. JSONの更新:
   python update_text_lines.py -j {target_dir}/02_text_lines.json -d temp_scripts/ocr.json
6. すべて問題なければ、`python step_executor.py 4` を実行すること。

[AIへの注意点]
- 問題がある場合は、停止。
""",
        4: f"""
========================================================================
【Step 4】 文字領域を背景色で塗り消去
========================================================================
[目的]
OCRで文字があると判定された領域のみを画像から塗りつぶし、クリーンな下敷きを作る。

[AIの実行手順]
1. current_working_folder.txtを読み取り、作業フォルダを確認すること。
2. 作業フォルダに01_raw_original.png、02_text_lines.jsonがあることを確認する。
3. 問題なければ、以下を実行する。
   python erase_text_regions.py -i {target_dir}/01_raw_original.png -j {target_dir}/02_text_lines.json -o {target_dir}/03_notext.png
4. 作業フォルダに03_notext.pngがあることを確認する。
5. すべて問題なければ、`python step_executor.py 5` を実行すること。

[AIへの注意点]
- 問題がある場合は、停止。
""",
        5: f"""
========================================================================
【Step 5】 文字領域の無い画像からパス抽出
========================================================================
[目的]
文字が消えた画像から再度パスを抽出し、純粋なイラストパーツのベクターパスを得る。

[AIの実行手順]
1. current_working_folder.txtを読み取り、作業フォルダを確認すること。
2. param_extract_paths.txtを読み取り、引数を確認すること。
3. 作業フォルダに03_notext.png、02_text_lines.jsonがあることを確認する。
4. 問題なければ、以下を実行する。2値化のパラメータは2で読み取ったABCDを利用する。
   python extract_paths.py {target_dir}/03_notext.png {target_dir} --prefix 05_notext --force {params_str}
5. 作業フォルダに以下のファイルが出力されていることを確認する。
  - 05_notext_metadata.json （各パスのバウンディングボックスや色の情報を持つJSONファイル）
  - 05_notext_combined.svg （抽出された全パスをまとめた単一のSVGファイル）
  - 05_notext_svgs/ （個別のパスがそれぞれ1つずつ保存されたフォルダ）
  - 05_notext_original.png （元画像のコピー）
6. すべて問題なければ、`python step_executor.py 6` を実行すること。

[AIへの注意点]
- 問題がある場合は、停止。
""",
        6: f"""
========================================================================
【Step 6】 部品クラスタリング
========================================================================
[目的]
抽出したパスの重なりを計算し、意味のあるコンポーネント（部品）単位の矩形（BBox）を自動計算する。

[AIの実行手順]
1. current_working_folder.txtを読み取り、作業フォルダを確認すること。
2. 作業フォルダに05_notext_metadata.jsonがあることを確認する。
3. 問題なければ、以下を実行する。
   python auto_cluster.py -m {target_dir}/05_notext_metadata.json -o {target_dir}/06_crop_config.json -v {target_dir}/06_cluster_visual.png
4. 06_crop_config.jsonと06_cluster_visual.pngが生成されたことを確認すること。
5. 生成された06_cluster_visual.pngをAIが目視確認し、部品が正しく分離されているか確認すること。
6. すべて問題なければ、`python step_executor.py 7` を実行すること。

[AIへの注意点]
- 問題がある場合は、停止。
""",
        7: f"""
========================================================================
【Step 7】 イラスト画像の切り出し
========================================================================
[目的]
Step 6で決定した部品矩形（06_crop_config.json）に従って、画像からイラストを切り出し（Crop）して保存する。

[AIの実行手順]
1. current_working_folder.txtを読み取り、作業フォルダを確認すること。
2. 作業フォルダに05_notext_original.png、06_crop_config.jsonがあることを確認する。
3. 問題なければ、以下を実行する。
   python crop_illustrations.py -c {target_dir}/06_crop_config.json -s {target_dir}/05_notext_original.png -d {target_dir}/07_crops
4. 07_crops/*.pngが生成されたことを確認すること。
5. すべて問題なければ、`python step_executor.py 8` を実行すること。

[AIへの注意点]
- 問題がある場合は、停止。
- 【黄金律】人物やアイコンを無理にベクターパスで表現してはいけない！ベクターパスを直接扱わない！
""",
        8: f"""
========================================================================
【Step 8】 統合SVGのビルド
========================================================================
[目的]
切り出したPNG画像と、AIが抽出したテキストを組み合わせて最終的なSVGを完成させる。

[AIへの実行手順]
1. current_working_folder.txtを読み取り、作業フォルダを確認すること。
2. 作業フォルダに05_notext_combined.svg、06_crop_config.json、02_text_lines.json、07_cropsフォルダがあることを確認する。
3. 問題なければ、以下を実行する。
   python build_final_svg.py -b {target_dir}/05_notext_combined.svg -c {target_dir}/06_crop_config.json -t {target_dir}/02_text_lines.json -i {target_dir}/07_crops -o {target_dir}/08_final.svg
4. 08_final.svgが生成されたことを確認すること。

[AIへの注意点]
- これが最終ステップです。完了後、成果物を報告してください。
"""
    }
    
    if step in steps:
        print(steps[step])
    else:
        print(f"[ERROR] 有効なステップ番号は 1 から {max(steps.keys())} です。")

def main():
    parser = argparse.ArgumentParser(description="AI Vector SVG Pipeline - Step Executor")
    parser.add_argument("step", type=int, help="実行したいステップ番号 (1-8)")
    args = parser.parse_args()
    
    get_step_instructions(args.step)

if __name__ == "__main__":
    main()
