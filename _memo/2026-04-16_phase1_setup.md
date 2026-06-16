# フェーズ1 セットアップ作業ログ

**ブランチ:** `feature/responses-api-refactor`  
**実施日:** 2026-04-16  
**対応フェーズ:** 改修プラン フェーズ1（実験準備）

---

## 実施内容

### 1. ブランチ作成
```
git checkout -b feature/responses-api-refactor
```

### 2. `.gitignore` 更新
以下を追加：
- `.devcontainer/` — Dev Container 設定
- `.venv/` — 仮想環境
- `_memo/` — ローカルメモ（本ファイルのフォルダ）
- `__pycache__/` / `*.pyc` — Python キャッシュ
- `.env` — API Key

### 3. `requirements.txt` 更新
```
openai>=1.66.0   # Responses API 対応バージョン
streamlit
python-dotenv    # .env からAPI Key を読み込む
```

### 4. 仮想環境の作成とパッケージインストール
```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```
インストール済みバージョン：openai==2.31.0、streamlit==1.56.0、python-dotenv==1.2.2

### 5. `.env.example` 作成
API Key のテンプレートとしてリポジトリにコミットするファイル。
```
OPENAI_API_KEY=your_api_key_here
```

### 6. `experiment/` ディレクトリ作成
- `experiment/.gitkeep` — 空ディレクトリを Git に追跡させるため

### 7. `plans/experiment_phrases.txt` 作成
旧辞書・新辞書の翻訳品質比較に使うテスト用標準語フレーズ10文。
日常会話（挨拶・体調・季節・温泉など）を収録。

### 8. `experiment/experiment.py` 作成
Responses API を使った辞書比較実験スクリプト。

**動作モード：**
| 状況 | 動作 |
|------|------|
| `dialect_dict.txt` のみ存在（フェーズ1） | 旧辞書として実行・記録 |
| `dialect_dict_old.txt` と `dialect_dict.txt` が両方存在（フェーズ2） | 旧・新を比較してサマリー出力 |

**主な仕様：**
- モデル: `gpt-5.4-mini`
- API: Responses API（`client.responses.create`）
- 各フレーズは独立リクエスト（`previous_response_id` なし）
- `max_output_tokens=200` で応答長を制限
- キャッシュヒット数（`cached_tokens`）もログ出力
- 結果を `plans/experiment_result.md` に保存

---

## 未実施（次のステップ）

- `.env` ファイルの作成（API Key の設定）
- 旧辞書のまま `experiment.py` を実行（フェーズ1 完了）
- フェーズ2: `dialect_dict.txt` を新書式に書き直し、比較実験

---

## 関連ファイル

| ファイル | 説明 |
|----------|------|
| `plans/improvement_plan.md` | 全体改修プラン |
| `plans/experiment_phrases.txt` | テスト用フレーズ |
| `experiment/experiment.py` | 実験スクリプト |
| `.env.example` | API Key テンプレート |
| `requirements.txt` | 依存パッケージ |
