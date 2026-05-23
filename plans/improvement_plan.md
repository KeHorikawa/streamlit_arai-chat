# 方言チャットボット改修プラン（最終版）

## Context

妙高市方言チャットボットの精度・機能向上を目的とした改修。
現状は `gpt-4o-mini` + Chat Completions API による単一チャットモードのみ。
自前APIで一般公開するためトークン消費の最小化が必須要件。
辞書書式変更前後の翻訳精度とトークン数を定量比較する実験も実施する。

---

## 参照ドキュメント

| 目的 | URL |
|------|-----|
| Responses API ガイド（概要・使い方） | https://platform.openai.com/docs/guides/responses |
| Responses API リファレンス（パラメーター詳細） | https://platform.openai.com/docs/api-reference/responses/create |
| 会話状態の管理（`previous_response_id`） | https://platform.openai.com/docs/guides/conversation-state |
| トークン使用量・コスト管理 | https://platform.openai.com/docs/guides/production-best-practices |
| openai Python SDK（GitHub） | https://github.com/openai/openai-python |

---

## 変更1: モデル変更

**ファイル:** `app.py`

```python
# Before
model="gpt-4o-mini",

# After
model="gpt-5.4-mini",
```

---

## 変更2: Chat Completions → Responses API

### 採用理由

| 観点 | Chat Completions（現状） | Responses API（新） |
|------|------------------------|---------------------|
| 会話履歴の送信 | 全メッセージを毎回送る | `previous_response_id` で参照するだけ |
| 会話が長くなると | 履歴トークンが増え続ける | 増えない |
| 辞書（instructions） | 毎回送る | 毎回送る（同じ） |
| コンテキスト超過 | 自分で管理 | `truncation="auto"` で自動処理 |
| レスポンステキスト取得 | `response.choices[0].message.content` | `response.output_text` |
| OpenAIの推奨 | 旧来 | **現在の推奨** |

### `requirements.txt` の更新

Responses APIはopenai Python SDK **1.66.0以降**で利用可能。

```
openai>=1.66.0
streamlit
```

### チャットモードの実装

```python
# 1回目
response = client.responses.create(
    model="gpt-5.4-mini",
    instructions=system_prompt,        # 辞書入り、毎回送る
    input=user_message,
    truncation="auto"
)
assistant_reply = response.output_text
st.session_state.last_response_id = response.id

# 2回目以降（履歴は送らず、IDで参照するだけ）
response = client.responses.create(
    model="gpt-5.4-mini",
    instructions=system_prompt,        # instructionsは毎回必要
    previous_response_id=st.session_state.last_response_id,
    input=user_message,
    truncation="auto"
)
assistant_reply = response.output_text
st.session_state.last_response_id = response.id
```

### 翻訳モードの実装

毎回独立したリクエスト（`previous_response_id` なし）：

```python
response = client.responses.create(
    model="gpt-5.4-mini",
    instructions=translation_prompt,   # 辞書入り
    input=user_message,
    max_output_tokens=200
)
translated_text = response.output_text
```

---

## 変更3: 2モード構成

### セッション状態の設計

```python
st.session_state.last_response_id    # チャットモード用（直前の応答ID）
st.session_state.chat_display        # 画面表示用の会話ログ（APIには送らない）
st.session_state.translation_display # 翻訳結果の表示ログ
st.session_state.conversation_count  # チャットモード用カウント
```

**モード切替時:** 上記すべてをリセットする。

### UIレイアウト

サイドバーにラジオボタンでモード切替：

```python
with st.sidebar:
    selected_mode = st.radio(
        "モード選択",
        ["チャットモード", "翻訳モード"],
        key="mode_selector"
    )
```

### チャットモード

- 会話上限10回、入力30文字制限は維持
- `instructions`（辞書付きシステムプロンプト）は毎回送信
- `previous_response_id` で会話を継続
- モード切替時: `last_response_id` をリセット → 会話がリセットされる

### 翻訳モード

- 対訳表示（`st.columns(2)`）:
  ```
  | 標準語          | 方言              |
  |-----------------|-------------------|
  | 今日はいい天気  | 今日はええ天気だねや |
  ```
- 毎回独立リクエスト（前の翻訳履歴は送らない）
- `max_output_tokens=200` で応答長を制限
- 回数制限なし

---

## 変更4: トークン節約まとめ

| 施策 | 対象 | 効果 |
|------|------|------|
| `previous_response_id` で会話継続 | チャットモード | 会話履歴トークンが増えない |
| 翻訳ごとに独立リクエスト | 翻訳モード | 毎回最小限のトークン |
| `max_output_tokens=200` | 翻訳モード | 応答が不必要に長くなるのを防ぐ |
| `truncation="auto"` | チャットモード | コンテキスト超過を自動処理 |
| 辞書（instructions）トークン | 両モード | 固定コスト・削減不可 |

---

## 変更5: 辞書書式変更

**ファイル:** `dialect_dict.txt`（完全書き直し）

**現状の問題:** 単語・文法ルール・会話例が混在 → LLMがルールと例文を区別しにくい

**新書式（3セクション構成）:**

```
## 文法・語法ルール        ← LLMが最優先で参照するルール集
〜だから → 〜すけ / 〜だすけ
〜ねぇ（終助詞）→ 〜ねや
〜ないで → 〜なや
〜てください → 〜てくんないや
〜てくれない → 〜てくんねかね
〜ますか/でしょうか → 〜かね / 〜ねかね
〜ときたら/〜ばかりは → 〜ばっかしゃ

## 語彙（品詞別）            ← カテゴリ整理で検索精度アップ

### 人称代名詞
私 → おら
あなた/君 → おまん
お前たち/君たち → おまんた

### 時間表現
昨日 → きんな
一昨日 → おってな
...（既存エントリを品詞別に整理）

## 会話例                    ← Few-shotとして機能（ルール・語彙とは分離）
（既存の対話例をそのまま掲載）
```

---

## 変更6: 辞書比較実験

**目的:** 旧辞書と新辞書の翻訳品質・トークン数を定量比較する

### ファイル構成

```
experiment/phase2/
  experiment.py             # 比較実験スクリプト
  phrases.txt               # テスト用標準語フレーズリスト（手動で用意）
  result.md                 # 実験結果（スクリプト実行後に自動生成）
dialect_dict_old.txt        # 旧辞書のバックアップ
```

### `experiment_phrases.txt` の内容例

```
今日はいい天気ですね。
私はとても疲れました。
あなたはうるさいですよ。
昨日、何をしていましたか？
このご飯はとても美味しいです。
恥ずかしくてたまりません。
それは大変でしたね。
では、またね。
```

### `experiment.py` の動作

1. `experiment/phase2/phrases.txt` からフレーズリストを読み込む
2. 旧辞書 / 新辞書をそれぞれ読み込む
3. 各フレーズをResponses APIで翻訳（独立リクエスト・`previous_response_id` なし）
4. `response.usage` からトークン数を取得:
   ```python
   input_tokens  = response.usage.input_tokens
   output_tokens = response.usage.output_tokens
   total_tokens  = response.usage.total_tokens
   ```
5. 結果を `experiment/phase2/result.md` に出力

### 出力形式

```markdown
## 旧辞書

| # | 標準語 | 翻訳結果 | 入力Token | 出力Token | 合計Token |
|---|--------|----------|-----------|-----------|-----------|
| 1 | 今日はいい天気ですね。 | 今日はええ天気だねや。 | 320 | 18 | 338 |
| **合計** | | | 2,560 | 144 | 2,704 |

## 新辞書

| # | 標準語 | 翻訳結果 | 入力Token | 出力Token | 合計Token |
|---|--------|----------|-----------|-----------|-----------|
| 1 | 今日はいい天気ですね。 | 今日はええ天気だねや。 | 280 | 16 | 296 |
| **合計** | | | 2,240 | 138 | 2,378 |

## 比較サマリー

| 指標 | 旧辞書 | 新辞書 | 差分 |
|------|--------|--------|------|
| 合計入力Token | 2,560 | 2,240 | -320 |
| 合計出力Token | 144 | 138 | -6 |
| 合計Token | 2,704 | 2,378 | -326 |
```

---

## 実装手順

### フェーズ1: 実験準備（辞書変更前）
1. `requirements.txt` を更新（`openai>=1.66.0`）
2. `experiment/phase2/phrases.txt` にテスト用フレーズを記入
3. `experiment/phase2/experiment.py` を作成（Responses API使用・トークン数取得込み）
4. **旧辞書のまま**実験を実行 → `experiment/phase2/result.md` に旧辞書の結果を保存

### フェーズ2: 辞書の書き直し・実験
5. `dialect_dict.txt` を `dialect_dict_old.txt` としてバックアップ
6. `dialect_dict.txt` を新書式に書き直す
7. 実験スクリプトを再実行 → `experiment/phase2/result.md` に新辞書の結果を追記・比較評価

### フェーズ2.5: 方言回答方式の比較実験
8. `experiment/phase25/phrases.txt` にテスト用フレーズを記入（ユーザーが作成）
9. `experiment/phase25/experiment_phase25.py` を作成（2パターンを同一フレーズで比較）
10. 実験を複数回実行し、結果を `experiment/phase25/result_run{n}.md` に保存

### フェーズ3: アプリ改修
8. `app.py` のAPIをResponses APIに変更（`client.responses.create`）
9. モデル名を変更
10. サイドバーのモード選択UIを追加
11. セッション状態の初期化ロジックを更新（モード切替でリセット）
12. チャットモード: `previous_response_id` による会話継続を実装
13. 翻訳モード: 独立リクエスト・対訳表示・`max_output_tokens` 設定

---

## 変更7: 方言回答方式の比較実験（フェーズ2.5）

**目的:** 方言精度を最大化するために、1ステップ回答と2ステップ回答のどちらが優れているかを定量比較する

### 比較パターン

| パターン | フロー | 概要 |
|----------|--------|------|
| A（直接） | 標準語の質問 → 方言の回答 | 1回のAPIリクエストで方言回答を生成 |
| B（2段階） | 標準語の質問 → 標準語の回答 → 方言の回答 | まず標準語で回答し、次のリクエストで方言に変換 |

### ファイル構成

```
experiment/phase25/
  experiment_phase25.py       # 比較実験スクリプト
  phrases.txt                 # テスト用フレーズリスト（ユーザーが作成）
  result_run1.md              # 実験結果 Run1
  result_run2.md              # 実験結果 Run2
```

### `experiment_phase25.py` の動作

1. `experiment/phase25/phrases.txt` からフレーズリストを読み込む
2. 各フレーズに対して2パターンでAPIリクエストを実行:
   - **パターンA:** `instructions`（辞書付き）+ `input`（標準語質問）→ 方言回答を1回で生成
   - **パターンB:** 1回目リクエストで標準語回答を生成 → 2回目リクエストで方言に変換
3. `response.usage` からトークン数を取得
4. 結果を `experiment/phase25/result_run{n}.md` に出力

### 出力形式

```markdown
## パターンA: 標準語質問 → 方言回答（直接）

| # | 標準語の質問 | 方言の回答 | 入力Token | 出力Token | 合計Token |
|---|------------|------------|-----------|-----------|-----------|
| 1 | 今日はどうでしたか？ | 今日はどうだったかね？ | 350 | 20 | 370 |
| **合計** | | | 3,500 | 200 | 3,700 |

## パターンB: 標準語質問 → 標準語回答 → 方言回答（2段階）

| # | 標準語の質問 | 標準語の回答 | 方言の回答 | 入力Token | 出力Token | 合計Token |
|---|------------|------------|------------|-----------|-----------|-----------|
| 1 | 今日はどうでしたか？ | 今日はどうでしたか？（標準語） | 今日はどうだったかね？ | 400 | 40 | 440 |
| **合計** | | | | 4,000 | 400 | 4,400 |

## 比較サマリー

| 指標 | パターンA（直接） | パターンB（2段階） | 差分 |
|------|------------------|-------------------|------|
| 合計Token | 3,700 | 4,400 | +700 |
| 方言精度（主観評価） | — | — | — |
```

---

## 検証方法

1. `python experiment/phase2/experiment.py` で実験スクリプトが正常に動作することを確認
2. `experiment/phase2/result.md` に旧辞書・新辞書のトークン数が記録されることを確認
3. `streamlit run app.py` で起動
4. チャットモード: 方言での会話が正しく動作することを確認
5. チャットモード: 10回上限・30文字制限が機能することを確認
6. 翻訳モード: 標準語入力 → 対訳（標準語|方言）が表示されることを確認
7. モード切替: サイドバーでモードを変えると状態がリセットされることを確認
