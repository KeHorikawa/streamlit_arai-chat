import streamlit as st
from openai import OpenAI

# OpenAI API Key
openai_api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=openai_api_key)

# 方言辞書の読み込み
with open('dialect_dict.txt', 'r') as file:
    dialects = file.read()

# チャット履歴の初期化
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "system", "content": f"""あなたは、方言でチャットするチャットボットです。\
         ユーザーの入力に応じて、方言を使って簡潔に答えます。\
         方言の辞書は、次のものを使います。\
         辞書は、標準語 => 方言 の書式です。\
         ### 辞書 ###\
         {dialects}"""}
    ]
    st.session_state.conversation_count = 0  # 会話回数を初期化

# ユージレイアウト
st.title("方言チャットボット")
st.write("妙高市の方言を使って会話してみましょう！")

# メインコンテナ
main_container = st.container()

with main_container:
    # 会話回数の表示
    st.write(f"残りの会話回数: {10 - st.session_state.conversation_count}")
    # チャット履歴を表示するコンテナ
    chat_container = st.container()
    # チャット履歴の表示
    with chat_container:
        for message in st.session_state.chat_history[1:]:  # システムメッセージをスキップ
            if message["role"] == "user":
                st.write(f"あなた: {message['content']}")
            elif message["role"] == "assistant":
                st.write(f"ボット: {message['content']}")
    # 入力セクション
    input_container = st.container()
    with input_container:
        if st.session_state.conversation_count < 10:
            user_input = st.text_input(
                "あなた: ",
                key=f"user_input_{st.session_state.conversation_count}"
            )

            if st.button("送信", key=f"send_{st.session_state.conversation_count}"):
                if user_input:
                    # ユーザーのメッセージを履歴に追加
                    st.session_state.chat_history.append(
                        {"role": "user", "content": user_input}
                    )

                    # OpenAI APIを使用して応答を生成
                    try:
                        response = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=st.session_state.chat_history,
                            temperature=0.3
                        )
                        assistant_reply = response.choices[0].message.content

                        # チャット履歴に追加
                        st.session_state.chat_history.append(
                            {"role": "assistant", "content": assistant_reply}
                        )

                        # 会話回数を増加
                        st.session_state.conversation_count += 1
                        # ページを再読み込みして新しい入力フィールドを表示
                        st.rerun()

                    except Exception as e:
                        st.error(f"APIエラー: {e}")
                else:
                    st.warning("メッセージを入力してください！")
        else:
            st.write("しゃべった回数が10回になったわね。また、始めからやってくんないや！")
            st.stop()
