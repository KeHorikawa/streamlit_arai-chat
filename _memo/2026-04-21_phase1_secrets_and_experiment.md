# フェーズ1 API Key 移行 & 実験実施ログ

**ブランチ:** `feature/responses-api-refactor`  
**実施日:** 2026-04-21  
**対応フェーズ:** 改修プラン フェーズ1（実験準備 → 実験完了）

---

## 実施内容

### 1. API Key 管理を `.env` → `.streamlit/secrets.toml` に移行

`.env` はセキュリティリスクがあるとの指摘を受け、Streamlit 推奨の `secrets.toml` 方式に変更。

**作成・変更ファイル：**

| ファイル | 変更内容 |
|----------|----------|
| `.streamlit/secrets.toml` | API Key を記述する実ファイル（`.gitignore` 対象） |
| `.streamlit/secrets.toml.example` | テンプレートファイル（`.gitignore` 対象のため共有不可） |
| `.env.example` | 削除（不要になったため） |
| `requirements.txt` | `python-dotenv` → `tomli` に変更 |
| `experiment/experiment.py` | `load_dotenv()` → `tomli` で `secrets.toml` 読み込みに変更 |

**`experiment.py` の変更概要：**
```python
# 変更前
from dotenv import load_dotenv
load_dotenv()
api_key = os.environ.get("OPENAI_API_KEY")

# 変更後
import tomli as tomllib
with open(BASE_DIR / ".streamlit" / "secrets.toml", "rb") as f:
    _secrets = tomllib.load(f)
api_key = _secrets.get("OPENAI_API_KEY")
```

**補足：**
- `app.py` はもともと `st.secrets["OPENAI_API_KEY"]` を使用しており変更不要だった
- `tomllib` は Python 3.11 標準ライブラリだが、環境が Python 3.10 のため `tomli` パッケージで代替
- `.gitignore` の `!.streamlit/secrets.toml.example` 否定パターンはディレクトリ指定と併用できないため削除し `.streamlit/` 1行に整理

### 2. フェーズ1 実験実施（`experiment.py` 初回実行）

`dialect_dict_old.txt` が存在しないフェーズ1モードで実行。現在の辞書を旧辞書として記録。

```
.venv/bin/python experiment/experiment.py
```

**結果：**
- フレーズ数: 10
- 全フレーズの翻訳成功
- 結果を `plans/experiment_result.md` に保存

**トークン使用状況（代表値）：**
| フレーズ | 入力Token | キャッシュ | 出力Token |
|----------|-----------|------------|-----------|
| 1フレーズ目 | 3,539 | 0 | 15 |
| 2フレーズ目以降 | 3,545〜3,566 | 3,328 | 16〜44 |

- 2フレーズ目以降はシステムプロンプト（辞書）の 3,328 トークンがキャッシュヒット
- 入力トークン数が全フレーズでほぼ同じなのは辞書（約3,300トークン）が大部分を占めるため

---

## 未実施（次のステップ）

- フェーズ2: `dialect_dict.txt` を新書式に書き直し
- `dialect_dict.txt` → `dialect_dict_old.txt` にリネームしてバックアップ
- 新辞書で `experiment.py` を再実行し、旧辞書と比較

---

## 関連ファイル

| ファイル | 説明 |
|----------|------|
| `plans/improvement_plan.md` | 全体改修プラン |
| `plans/experiment_phrases.txt` | テスト用フレーズ |
| `plans/experiment_result.md` | フェーズ1 実験結果 |
| `experiment/experiment.py` | 実験スクリプト |
| `.streamlit/secrets.toml` | API Key（gitignore対象） |
| `requirements.txt` | 依存パッケージ |
