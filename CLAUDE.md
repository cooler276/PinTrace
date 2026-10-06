# PinTrace — crazyflie-firmware 機能設計リバースエンジニアリング

## 目的
`crazyflie-firmware/` のソースコードから機能設計を逆起こしし、Markdown + Mermaid の設計書として `design/` にまとめる。
ブロック図（機能間の関係）とデータフローの可視化を重視する。

## 前提
- 対象: ファームウェア全体。基準構成は **cf2**（`configs/cf2_defconfig`）。他プラットフォーム（bolt / tag / flapper / cf21bl）との差分は必要に応じて注記する。
- 解析対象のコミット: `crazyflie-firmware` の HEAD（`9cf9d86c`、2026-09-24）。設計書の記述はこのコミットに基づく。
- `crazyflie-firmware/` は**読み取り専用**として扱い、編集しない。
- `vendor/`（FreeRTOS, CMSIS, libdw1000）は外部ライブラリとして扱い、中身は設計対象外。呼び出し側の使い方だけを書く。

## ディレクトリ
| パス | 内容 | git管理 |
|---|---|---|
| `crazyflie-firmware/` | 解析対象（upstream clone、submodule 取得済み） | 対象外 |
| `tools/` | 解析用スクリプト | ○ |
| `analysis/config/<platform>/` | Kconfig 解決結果（`.config`, `autoconf.h`）、ビルド対象ファイル一覧（`filelist.txt`）、非対象（`excluded.txt`） | ○ |
| `analysis/ctags/<platform>/` | `tags` / `tags.json`（シンボル索引） | 対象外（再生成可） |
| `analysis/doxygen/<platform>/` | `html/`（コールグラフ閲覧用）、`xml/`（スクリプト抽出用） | 対象外（再生成可） |
| `design/` | **成果物**：機能設計書 | ○ |

## 解析データの再生成
```powershell
powershell -ExecutionPolicy Bypass -File tools\setup_analysis.ps1 -Platform cf2   # 全部（doxygen 約2.5分）
python tools\check_mermaid.py                                                     # design/ の Mermaid 構文検証
python tools\include_deps.py --depth 1                                            # レイヤ間の #include 依存数（--depth 2 / --file-level も可）
python tools\doxy_index.py enclosing <file> <line>                                # その行を含む関数
python tools\doxy_index.py callers|callees <func>                                 # 呼び出し元 / 呼び出し先（static 関数は name@file で指定）
python tools\doxy_index.py chain <func> --depth 6                                 # 呼び出し元を遡る
python tools\list_param_log.py [--kind param|log]                                 # param / log のグループと変数の一覧（TSV）
python tools\collect_open_issues.py                                               # 各文書の「未解決事項」を 99_appendix/open_issues.md に集約
python tools\gen_layer_diagrams.py                                                # 階層構造の図 A/B/C（00_overview/layers_*.svg）
python tools\io_paths.py                                                          # 入力 → 判断 → 出力の経路の分析（02_dataflow/io_paths.md の自動生成部と図）
```
- 文書の「未解決事項」を直したら、`collect_open_issues.py` で `open_issues.md` を再生成する（マーカーより上の手書き部分は保持される）。
- Doxygen の既知の対策（`tools/run_doxygen.py`）: `/**` で始まる Bitcraze の ASCII アートのバナーは、行末の `\` のせいで以降の宣言が全部消えるので、`tools/doxy_filter.py` で `/*` に変えている。`__attribute__` と `STATIC_MEM_*_ALLOC` は PREDEFINED で空にしている。Doxygen が認識する関数は、`src/lib` を除いて ctags の約 90%（残りは `#ifdef` で無効なコード）。
- Doxygen の呼び出しグラフは `#ifdef` を取りこぼすことがある（例: `systemTask` → `proximityInit`）。結論に使う前に、呼び出し箇所の `#ifdef` をソースで確認する。
- 図のレイアウトを目で確認するときは、`check_mermaid.py` が `analysis/mermaid/*.mmd` に書き出した図を `mmdc -i <mmd> -o <png> -s 1.5 -b white` で PNG にして見る。
- Graphviz は PATH 未登録。`tools/run_doxygen.py` の `DOT_PATH` で指定している。
- 新しい PowerShell 以外では PATH が古い場合があるので、`node`/`mmdc` が見つからなければ PATH を再読込する。

## 解析の進め方
- どのファイルが cf2 でビルドされるかは `analysis/config/cf2/filelist.txt` を正とする。`excluded.txt` にあるファイルは cf2 では存在しない機能として扱う。
- `#ifdef CONFIG_*` は `analysis/config/cf2/.config` の値で判断する。
- 呼び出し関係は Doxygen XML の `<references>` / `<referencedby>` を使う。ただし関数ポインタ経由の呼び出し（controller / estimator / deck driver の切替など）は Doxygen が追えないので、ソースを読んで補う。
- FreeRTOS のタスク・キュー・セマフォ、CRTP ポート、param/log 変数は機能間のデータの受け渡しの要所なので、優先的に洗い出す。
- `crazyflie-firmware/docs/` の公式ドキュメントは答え合わせに使う。記述が食い違う場合はソースを正とし、食い違いを注記する。

## 設計書の書き方（design/）
- 日本語で書く。識別子（関数名・型名・ファイル名）は原文のままコード表記にする。
- 根拠となるソースを `src/modules/src/stabilizer.c:289` の形式で示す（パスは firmware ルートからの相対パス）。
- ソースから確認した事実と推測を区別する。推測には **（推測）** を付け、未解明の点は各ドキュメント末尾の「未解決事項」に書く。
- 図は Mermaid で描く。ブロック図は `flowchart`、処理の順序は `sequenceDiagram`、状態遷移は `stateDiagram-v2` を使う。1つの図のノード数は目安として30以下に抑え、大きい場合は図を分ける。
- 図を追加・変更したら `python tools/check_mermaid.py` で検証する。
- Mermaid で配置を制御できない図（層を上下に固定しつつ上向きの矢印を描くなど）に限り、Graphviz で描いて SVG を埋め込む。階層構造の 3 枚の図（`design/00_overview/layers_*.svg`）は `python tools/gen_layer_diagrams.py` で生成し、要素・関係の追加や修正はスクリプトの定義を直す。
- 図は「呼び出し（誰が誰を呼ぶか）」と「データフロー（何がどこへ渡るか）」を区別する。ポインタ経由で構造体を書き換える関数（例: 衝突回避）は、呼び出しの図だけでは影響範囲が見えない。
- ドキュメントの構成と索引は `design/README.md` を参照する。
