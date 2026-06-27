# 妙高市 方言チャットボット

新潟県妙高市（旧新井市）の方言「妙高弁」で会話できる Streamlit アプリです。地元のおばあちゃんと話す「チャットモード」と、標準語を妙高弁に変換する「翻訳モード」の2つを備えています。

## 機能

- **チャットモード** — 妙高市に生まれ育った設定のキャラクターと、妙高市の観光・自然・食・歴史・文化などについて方言で会話できます（1セッション最大10ターン）。
- **翻訳モード** — 入力した標準語を妙高弁に翻訳します。
- 方言の語彙・表現は `dialect_dict.txt`（妙高弁辞書）に基づいて生成され、辞書外の表現を使わないよう制御しています。

## 技術スタック

- [Streamlit](https://streamlit.io/) — UI
- [OpenAI API](https://platform.openai.com/)（Responses API） — 応答生成
- Python 3.11+

## セットアップ

### 1. リポジトリを取得

```bash
git clone https://github.com/KeHorikawa/streamlit_arai-chat.git
cd streamlit_arai-chat
```

### 2. 仮想環境の作成と依存関係のインストール

```bash
python -m venv .venv
source .venv/bin/activate        # Windows は .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. APIキーの設定

`.streamlit/secrets.toml.example` をコピーして `.streamlit/secrets.toml` を作成し、OpenAI の API キーを設定します。

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

```toml
# .streamlit/secrets.toml
OPENAI_API_KEY = "your_api_key_here"
```

> `.streamlit/secrets.toml` は `.gitignore` に登録されており、リポジトリにはコミットされません。

## 実行

```bash
streamlit run app.py
```

ブラウザで `http://localhost:8501` を開くとアプリが表示されます。

## プロジェクト構成

```
.
├── app.py                  # アプリ本体（チャット／翻訳の2モード）
├── dialect_dict.txt        # 妙高弁辞書（語彙・表現・文法ルール・文末表現）
├── requirements.txt        # 依存パッケージ
├── .streamlit/
│   └── secrets.toml.example # APIキー設定のテンプレート
├── experiment/             # 方言生成の検証用スクリプト・結果
│   └── prompt_dict_lab/    # プロンプト・辞書 改善実験ハーネス（汎用）
├── plans/                  # 改修・実験の計画ドキュメント
└── _memo/                  # 開発メモ・実験記録
```

## プロンプト・辞書 改善実験（experiment/prompt_dict_lab）

辞書（`dialect_dict.txt`）とチャット用プロンプトの改善を、**新旧を入れ替えながら定量・定性比較**するための汎用実験ディレクトリを用意しています。今回限りでなく、今後のプロンプト・辞書改善でも同じ仕組みで繰り返し使えます。

- プロンプト・辞書・テスト用フレーズを `variants/`・`phrases/` 配下のテキストファイルとして外部化。
- `config.toml` で「アーム（プロンプト × 辞書の組み合わせ）」を宣言し、同一フレーズに流して横並び比較。
- 結果は `results/` に保存され、出力の横並び（定性評価）とトークン消費（定量）の両方が残ります。
- コード本体（`run_experiment.py`）を変更せず、設定とテキストの追加だけで新しい実験を足せます。

```bash
python experiment/prompt_dict_lab/run_experiment.py
```

詳しい使い方・拡張手順は [`experiment/prompt_dict_lab/README.md`](experiment/prompt_dict_lab/README.md) を参照してください。

## デプロイ

[Streamlit Community Cloud](https://streamlit.io/cloud) にデプロイできます。アプリの「Secrets」設定に `OPENAI_API_KEY` を登録してください。`requirements.txt` をもとに環境が構築されます。

## ライセンス

個人プロジェクトです。
