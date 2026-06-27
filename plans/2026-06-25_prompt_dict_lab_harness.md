# プロンプト・辞書 改善 実験ハーネス 実装計画

作成日: 2026-06-25
ブランチ: `experiment/prompt-dict-lab`

## Context

プロンプトと辞書の改善（直近は文末表現の自然さ、[[2026-06-25_dialect_naturalness_improvement]] 参照）を、
**新旧を入れ替えて定量・定性比較**しながら継続的に回したい。既存の `experiment/phase2`・
`phase25` はプロンプトをスクリプトにハードコードしており、改善のたびにコード編集が要る。
そこで、プロンプト・辞書・フレーズを外部ファイル化し、設定だけ差し替えて回せる汎用ハーネスを
`experiment/prompt_dict_lab/` に用意する。今回の文末改善はその最初の利用ケース。

## ゴール / 非ゴール

**ゴール**
- プロンプトと辞書を新旧（または複数案）入れ替えて、同一フレーズで横並び比較できる。
- コードを触らず、設定ファイル（`config.toml`）とテキスト追加だけで新実験を足せる。
- 結果に「出力の横並び（定性）」と「トークン消費（定量）」の両方が残る。
- 今後のあらゆるプロンプト・辞書改善で使い回せる。

**非ゴール（今回はやらない）**
- マルチターン会話の自動評価（単発入力で評価する。必要になったら拡張）。
- 自動採点・LLM-as-judge（まずは人手の定性評価＋トークン定量）。
- app.py 本体への反映（実験で良ければ別途反映する）。

## ディレクトリ構成

```
experiment/prompt_dict_lab/
├── README.md            # 使い方・拡張手順
├── config.toml          # 実験設定（アーム・モデル・フレーズ・タイトル）
├── run_experiment.py    # 汎用ランナー
├── variants/
│   ├── prompts/         # プロンプト候補（{dict_content} 差し込み可）
│   └── dicts/           # 辞書候補
├── phrases/             # テスト入力（1行1フレーズ、# と空行無視）
└── results/             # {title}_run{n}.md を自動保存
```

## 設計

### アーム方式

- **アーム = プロンプト1つ × 辞書1つ**。`config.toml` の `[[arms]]` で宣言。
- 2アーム以上を同じフレーズ集に流し、横並びで比較する（2案でも3案でも可）。
- プロンプトに `{dict_content}` プレースホルダがあればその辞書を差し込む。無ければ素通し
  （辞書を使わないプロンプト比較も可能）。

### config.toml スキーマ

```toml
title = "dialect_sentence_end"   # 結果ファイル名の接頭辞
model = "gpt-5.4-mini"
max_output_tokens = 300
phrases = "phrases/dialect_naturalness.txt"

[[arms]]
name = "baseline"
prompt = "variants/prompts/chat_v1_baseline.txt"
dict = "variants/dicts/dict_v1_baseline.txt"

[[arms]]
name = "v2_sentence_end"
prompt = "variants/prompts/chat_v2_sentence_end.txt"
dict = "variants/dicts/dict_v2_sentence_end.txt"
```

### ランナー (`run_experiment.py`) の処理

1. `.streamlit/secrets.toml` から `OPENAI_API_KEY` を読む（既存実験と同方式）。
2. `config.toml` を読み、フレーズ・アームを解決（パスは lab ディレクトリ基準）。
3. 各アームで全フレーズを Responses API（`client.responses.create`）に単発投入。
4. 出力テキストとトークン使用量（入力/キャッシュ/出力/合計）を収集。
5. 結果 Markdown を `results/{title}_run{n}.md` に保存:
   - 出力の横並び比較表（定性評価用）
   - トークン比較サマリー（定量）
   - アーム別詳細表
6. `n` は既存の空でない結果を避けて自動採番（上書きしない）。

### 既存実験との関係

- `phase2`・`phase25` は当時の記録として残す（移行しない）。
- 新規のプロンプト・辞書改善は今後すべて `prompt_dict_lab` で行う。

## 実装ステップ（このブランチでの作業）

1. [x] ブランチ `experiment/prompt-dict-lab` を作成。
2. [x] ディレクトリ構成を作成。
3. [x] `run_experiment.py`（汎用ランナー）を実装。
4. [x] `variants/dicts/dict_v1_baseline.txt` = 現行辞書スナップショット。
5. [x] `variants/dicts/dict_v2_sentence_end.txt` = 文末表現セクション追加版。
6. [x] `variants/prompts/chat_v1_baseline.txt` = 現行チャットプロンプト相当。
7. [x] `variants/prompts/chat_v2_sentence_end.txt` = 文末ルール追加・制約緩和版。
8. [x] `phrases/dialect_naturalness.txt` = 文末問題を再現する会話フレーズ。
9. [x] `config.toml` = baseline vs v2_sentence_end の2アーム。
10. [x] `README.md` = 使い方・拡張手順。
11. [ ] `python run_experiment.py` を実行し、`results/` に初回結果を生成。
12. [ ] 結果を定性評価（下記の評価観点）し、所見を `_memo/` か results 末尾に記録。

## 評価観点（文末改善の検証）

- 文末が「〜よ」で終わる文の割合が baseline より下がっているか。
- 「わね / ねや / んだわ」が（単調にならず）分散して出ているか。
- 否定が「〜ない」→「〜ねえ」になっているか。
- 語彙の造語（辞書外の方言）が増えていないか（制約緩和の副作用チェック）。
- トークン消費が許容範囲か（文末セクション追加による入力増の確認）。

## 今後の拡張余地

- マルチターン対応（`previous_response_id` を使う会話シナリオ単位の比較）。
- LLM-as-judge による自動採点アーム。
- フレーズ集のテーマ別分割（観光・食・生活など）。
- 同一アームの複数回試行による出力ぶれの確認（temperature 影響）。
```
