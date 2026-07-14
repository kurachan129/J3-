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
