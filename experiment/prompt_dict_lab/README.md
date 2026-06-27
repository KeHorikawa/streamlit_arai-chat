# prompt_dict_lab — プロンプト・辞書 改善実験ハーネス

プロンプトと辞書を**新旧入れ替えながら**方言の自然さやトークン消費を比較するための、
使い回せる実験環境。今回限りでなく、今後のプロンプト・辞書改善でも同じ仕組みで回す。

## 構成

```
prompt_dict_lab/
├── README.md            # このファイル
├── config.toml          # 実験設定（どのアームを比較するか）
├── run_experiment.py    # 汎用ランナー（コードは触らない）
├── variants/
│   ├── prompts/         # プロンプト候補（{dict_content} を含められる）
│   │   ├── chat_v1_baseline.txt
│   │   └── chat_v2_sentence_end.txt
│   └── dicts/           # 辞書候補
│       ├── dict_v1_baseline.txt      # 現行 dialect_dict.txt のスナップショット
│       └── dict_v2_sentence_end.txt  # 文末表現セクション追加版
├── phrases/             # テスト入力（1行1フレーズ。# と空行は無視）
│   └── dialect_naturalness.txt
└── results/             # 実行結果（{title}_run{n}.md として自動保存）
```

## 用語

- **アーム (arm):** 「プロンプト1つ × 辞書1つ」の組み合わせ。比較の1条件。
- **フレーズ:** 各アームに同じ条件で投げる入力文の集合。

## 使い方

```bash
# 既定の config.toml で実行
python experiment/prompt_dict_lab/run_experiment.py

# 別の設定ファイルで実行
python experiment/prompt_dict_lab/run_experiment.py --config config.toml
```

実行すると `results/{title}_run{n}.md` が生成される。中身は:

1. **出力の横並び比較** — 同じフレーズに対する各アームの出力を並べた定性評価表
2. **トークン比較サマリー** — アームごとの入力/キャッシュ/出力/合計トークン
3. **アーム別詳細** — アームごとの全フレーズ結果

## 新しい実験を足す手順

1. `variants/prompts/` か `variants/dicts/` に候補ファイルを追加する。
   - プロンプトに `{dict_content}` を書くと、そのアームの辞書が差し込まれる。
   - 辞書だけ・プロンプトだけを変えたいときは、もう片方は既存ファイルを使い回す。
2. `config.toml` の `[[arms]]` を編集（または新しい config を作成）。
   - `title` を変えると結果ファイル名が変わる（実験ごとに分かれる）。
   - フレーズを変えるなら `phrases/` に追加して `phrases` を差し替え。
3. `run_experiment.py` を実行。コード本体は変更不要。

## 前提

- `.streamlit/secrets.toml` に `OPENAI_API_KEY` が必要。
- 依存: `openai`, `tomli`（`requirements.txt` 参照）。
