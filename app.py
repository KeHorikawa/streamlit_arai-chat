import streamlit as st
from openai import OpenAI

openai_api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=openai_api_key)

MODEL = "gpt-5.4-mini"
MAX_TURNS = 10
MAX_INPUT_CHARS = 50

with open("dialect_dict.txt", encoding="utf-8") as f:
    dialect_dict = f.read()


def build_chat_prompt(dialect_dict: str) -> str:
    return f"""あなたは新潟県妙高市に生まれ育った70歳前後の女性です。
妙高市の文化・歴史・風土・暮らしについて深い知識を持ち、観光客や妙高市に興味を持つ方の質問に、温かく簡潔に答えます。

【対応するテーマ】
以下に関係する質問にだけ答えてください。
- 妙高市・上越地方の観光・自然・食・行事・歴史・文化・風土・暮らし・方言
- 新潟県に関連する話題（妙高市との関連がある範囲）

【対応しないテーマ】― 厳守 ―
上記と無関係な質問（政治・経済・技術・他地域の話・一般的な知識問答など）には答えません。
その場合は、以下のような一言だけを返してください。キャラクターを崩さず、説明や謝罪は不要です。

返答例（自然に使い分けてよい）：
- 「あ〜、それはわからんね。」
- 「さあ、そこまではわからんねぇ。」
- 「それは、ちょっとわたしにはなんとも。」

【話し方の基本】
- 親しみやすく、ゆったりとした話し方
- 難しい説明は避け、わかりやすく、でも地元らしさが伝わる表現で

【方言の使い方】― 厳守 ―
以下の「妙高弁辞書」に載っている言葉・表現だけを方言として使ってください。
辞書に載っていない方言・語尾・イントネーションは使ってはいけません。
辞書にない部分は自然な標準語（または丁寧なやわらかい日本語）で話してください。
辞書の言葉を無理に詰め込まず、会話の流れで自然に使える場面だけで使う。

【妙高弁辞書】
{dialect_dict}

【回答スタイル】
- 質問への答えは簡潔に（長くなりすぎない）
- 必要なら「妙高ではね、〇〇なんですよ」のように地元目線を添える"""


def build_translation_prompt(dialect_dict: str) -> str:
    return f"""あなたは、標準語を妙高市の方言（妙高弁）に翻訳するシステムです。
入力された標準語テキストを、以下の辞書に記載された語彙・文法ルールを使って妙高弁に翻訳してください。
翻訳結果のみを出力し、説明や補足は不要です。

【妙高弁辞書】
{dialect_dict}"""


CHAT_PROMPT = build_chat_prompt(dialect_dict)
TRANSLATION_PROMPT = build_translation_prompt(dialect_dict)


def init_session():
    if "current_mode" not in st.session_state:
        st.session_state.current_mode = None
    if "last_response_id" not in st.session_state:
        st.session_state.last_response_id = None
    if "chat_display" not in st.session_state:
        st.session_state.chat_display = []
    if "translation_display" not in st.session_state:
        st.session_state.translation_display = []
    if "conversation_count" not in st.session_state:
        st.session_state.conversation_count = 0


def reset_state():
    st.session_state.last_response_id = None
    st.session_state.chat_display = []
    st.session_state.translation_display = []
    st.session_state.conversation_count = 0


init_session()

st.title("妙高市 方言チャットボット")

with st.sidebar:
    selected_mode = st.radio(
        "モード選択",
        ["チャットモード", "翻訳モード"],
        key="mode_selector",
    )

if st.session_state.current_mode != selected_mode:
    st.session_state.current_mode = selected_mode
    reset_state()

# ── チャットモード ──────────────────────────────────────────────────────
if selected_mode == "チャットモード":
    st.write("妙高市の言葉で、地元のおばあちゃんと話してみましょう！")
    st.caption(f"残り会話回数: {MAX_TURNS - st.session_state.conversation_count} / {MAX_TURNS}")

    chat_container = st.container()
    with chat_container:
        for turn in st.session_state.chat_display:
            st.write(f"**あなた:** {turn['user']}")
            st.write(f"**ボット:** {turn['bot']}")
            st.divider()

    if st.session_state.conversation_count < MAX_TURNS:
        user_input = st.text_input(
            "メッセージを入力（30文字以内）:",
            key=f"chat_input_{st.session_state.conversation_count}",
        )
        if st.button("送信", key=f"chat_send_{st.session_state.conversation_count}"):
            if not user_input:
                st.warning("メッセージを入力してください！")
            elif len(user_input) > MAX_INPUT_CHARS:
                st.warning("長すぎるわね。もう少し短くして入力してくんないや！")
            else:
                try:
                    kwargs = dict(
                        model=MODEL,
                        instructions=CHAT_PROMPT,
                        input=user_input,
                        truncation="auto",
                    )
                    if st.session_state.last_response_id:
                        kwargs["previous_response_id"] = st.session_state.last_response_id

                    response = client.responses.create(**kwargs)
                    bot_reply = response.output_text

                    st.session_state.last_response_id = response.id
                    st.session_state.chat_display.append(
                        {"user": user_input, "bot": bot_reply}
                    )
                    st.session_state.conversation_count += 1
                    st.rerun()
                except Exception as e:
                    st.error(f"APIエラー: {e}")
    else:
        st.info("しゃべった回数が10回になったわね。また、始めからやってくんないや！")

# ── 翻訳モード ──────────────────────────────────────────────────────────
else:
    st.write("標準語を入力すると、妙高弁に翻訳します。")

    if st.session_state.translation_display:
        col1, col2 = st.columns(2)
        col1.markdown("**標準語**")
        col2.markdown("**妙高弁**")
        for entry in st.session_state.translation_display:
            col1.write(entry["standard"])
            col2.write(entry["dialect"])
            col1.divider()
            col2.divider()

    user_input = st.text_input(
        "翻訳したい標準語を入力:",
        key=f"trans_input_{len(st.session_state.translation_display)}",
    )
    if st.button("翻訳", key=f"trans_send_{len(st.session_state.translation_display)}"):
        if not user_input:
            st.warning("テキストを入力してください！")
        else:
            try:
                response = client.responses.create(
                    model=MODEL,
                    instructions=TRANSLATION_PROMPT,
                    input=user_input,
                    max_output_tokens=200,
                )
                dialect_text = response.output_text

                st.session_state.translation_display.append(
                    {"standard": user_input, "dialect": dialect_text}
                )
                st.rerun()
            except Exception as e:
                st.error(f"APIエラー: {e}")
