# Promotion Intelligence

> 試合を分析するのではなく、昇格を分析する。

J3昇格チームのMatch Report PDFを統一データベースへ変換し、KPI、Promotion Index、Game Similarityを算出するためのプロジェクトです。

## Initial milestone

1. PDF 1試合を読み込む
2. Page 1 / 3 / 7 / 8 / 9の主要指標を抽出する
3. チーム視点のJSONへ正規化する
4. SQLiteへ保存する
5. QC結果を出力する

## Principles

- レポートに存在する値だけを使用する
- 未収録・判読不能は `NULL` とする
- 観測された0だけを0として扱う
- 推測値を作らない
- すべてのRaw値に出典ページと品質フラグを持たせる

## Parser v1.0

### 対応形式

- DataStadium 2024 J3 Match Report（16または17ページ）
- DataStadium 2025 J3 Match Report（18ページ）
- 抽出対象ページ: Page 1 / 3 / 7 / 8 / 9

レポートに明記された数値のみを取得します。未収録または判読不能な値を
別項目から推測・補完せず、共通JSONでは `null` として出力します。

### PDFから共通JSONとQCを生成する

開発環境をインストールします。

```bash
python -m pip install -e '.[dev]'
```

1試合を共通JSONへ変換する場合:

```bash
promotion-intelligence parse reports/regression/GR_20240302_J3_02_大宮vs岐阜.pdf \
  --output outputs/omiya_gifu.json
```

ディレクトリ内のPDFを一括変換し、試合別JSON、QC CSV、QC JSON、項目別取得率を
生成する場合:

```bash
promotion-intelligence batch reports/regression outputs/parser_v1
```

主なQC生成物:

- `qc_results.csv` / `qc_results.json`: 試合別ステータスとNULL項目一覧
- `qc_field_capture.csv` / `qc_field_capture.json`: 項目別取得数、NULL数、取得率

### 回帰テスト

Parser v1.0は以下の11試合を回帰テスト対象としています。

- 2024 大宮アルディージャ: 第1〜10節
  - 大宮vs八戸、大宮vs岐阜、福島vs大宮、大宮vs奈良、相模原vs大宮
  - 大宮vs宮崎、北九州vs大宮、大宮vsFC大阪、YS横浜vs大宮、大宮vs沼津
- 2025 栃木シティ: 第19節 栃木Cvs琉球

PDFはGitへコミットせず、ローカルの `reports/regression/` に配置します。

```bash
pytest -q
ruff check .
```

## Planned structure

```text
src/promotion_intelligence/
  parser/
  database/
  analysis/
  app/
tests/
docs/
```
