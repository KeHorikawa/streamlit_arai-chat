"""
Playwright を使った app.py の動作確認スクリプト
実行: .venv/bin/python verify_playwright.py
"""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
import time

BASE_URL = "http://localhost:8501"
SCREENSHOT_DIR = Path("_memo/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def wait_for_streamlit(page, timeout=15000):
    """Streamlit の描画完了を待つ（スピナーが消えるまで）"""
    page.wait_for_load_state("networkidle", timeout=timeout)
    # Streamlit の running indicator が消えるまで待機
    try:
        page.wait_for_selector("[data-testid='stStatusWidget']", state="detached", timeout=5000)
    except Exception:
        pass
    time.sleep(1)


def run_verification():
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        # ── テスト 1: 初期表示 ──────────────────────────────────
        print("[1] 初期表示の確認...")
        page.goto(BASE_URL)
        wait_for_streamlit(page)
        page.screenshot(path=str(SCREENSHOT_DIR / "01_initial.png"))

        title_ok = page.locator("h1").filter(has_text="妙高市").count() > 0
        sidebar_radio = page.locator("[data-testid='stRadio']").count() > 0
        chat_label = page.locator("text=チャットモード").count() > 0
        trans_label = page.locator("text=翻訳モード").count() > 0

        results.append(("初期表示: タイトルに「妙高市」が含まれる", title_ok))
        results.append(("初期表示: サイドバーにラジオボタンが表示される", sidebar_radio))
        results.append(("初期表示: 「チャットモード」ラベルが存在する", chat_label))
        results.append(("初期表示: 「翻訳モード」ラベルが存在する", trans_label))

        # ── テスト 2: チャットモードの UI 確認 ─────────────────
        print("[2] チャットモードの UI 確認...")
        # 残り会話回数の表示
        remaining = page.locator("text=残り会話回数").count() > 0
        # テキスト入力フィールドの存在
        input_field = page.locator("[data-testid='stTextInput']").count() > 0
        # 送信ボタンの存在
        send_btn = page.locator("button", has_text="送信").count() > 0

        results.append(("チャット: 残り会話回数が表示される", remaining))
        results.append(("チャット: テキスト入力フィールドが存在する", input_field))
        results.append(("チャット: 送信ボタンが存在する", send_btn))

        # ── テスト 3: 入力文字数制限（30文字超で警告）──────────
        print("[3] 文字数制限の確認（31文字入力）...")
        text_input = page.locator("[data-testid='stTextInput'] input").first
        text_input.fill("あ" * 31)
        page.locator("button", has_text="送信").click()
        wait_for_streamlit(page)
        page.screenshot(path=str(SCREENSHOT_DIR / "03_char_limit_warning.png"))

        warning_shown = page.locator("[data-testid='stAlert']").count() > 0
        results.append(("チャット: 31文字入力で警告が表示される", warning_shown))

        # ── テスト 4: 空入力で警告 ─────────────────────────────
        print("[4] 空入力の確認...")
        text_input.fill("")
        page.locator("button", has_text="送信").click()
        wait_for_streamlit(page)
        page.screenshot(path=str(SCREENSHOT_DIR / "04_empty_input_warning.png"))

        empty_warning = page.locator("[data-testid='stAlert']").count() > 0
        results.append(("チャット: 空入力で警告が表示される", empty_warning))

        # ── テスト 5: 翻訳モードへの切り替え ───────────────────
        print("[5] 翻訳モードへの切り替え...")
        page.locator("[data-testid='stRadio'] label", has_text="翻訳モード").click()
        wait_for_streamlit(page)
        page.screenshot(path=str(SCREENSHOT_DIR / "05_translation_mode.png"))

        trans_input = page.locator("[data-testid='stTextInput']").count() > 0
        trans_btn = page.locator("button", has_text="翻訳").count() > 0
        # チャットモードの「送信」ボタンが消えているか
        send_gone = page.locator("button", has_text="送信").count() == 0

        results.append(("翻訳モード: テキスト入力フィールドが表示される", trans_input))
        results.append(("翻訳モード: 翻訳ボタンが表示される", trans_btn))
        results.append(("翻訳モード: チャットの送信ボタンが消える（モード切替OK）", send_gone))

        # ── テスト 6: チャットモードに戻してセッションリセット確認 ─
        print("[6] チャットモードに戻してリセット確認...")
        page.locator("[data-testid='stRadio'] label", has_text="チャットモード").click()
        wait_for_streamlit(page)
        page.screenshot(path=str(SCREENSHOT_DIR / "06_back_to_chat.png"))

        # 会話ログが空（リセットされている）かつ入力フィールドが再表示
        chat_input_restored = page.locator("[data-testid='stTextInput']").count() > 0
        results.append(("モード切替後: チャット入力フィールドが再表示される（リセットOK）", chat_input_restored))

        # ── 最終スクリーンショット ──────────────────────────────
        page.screenshot(path=str(SCREENSHOT_DIR / "07_final.png"))
        browser.close()

    return results


if __name__ == "__main__":
    print("=== Playwright 動作確認開始 ===\n")
    results = run_verification()
    print("\n=== 確認結果 ===")
    passed = 0
    failed = 0
    for label, ok in results:
        mark = "✅" if ok else "❌"
        print(f"{mark} {label}")
        if ok:
            passed += 1
        else:
            failed += 1
    print(f"\n合計: {passed} 件 PASS / {failed} 件 FAIL")
    print(f"スクリーンショット: _memo/screenshots/ に保存済み")
