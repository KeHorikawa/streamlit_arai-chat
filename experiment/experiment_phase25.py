import sys
import tomli as tomllib
from pathlib import Path
from openai import OpenAI

BASE_DIR = Path(__file__).parent.parent
_secrets_path = BASE_DIR / ".streamlit" / "secrets.toml"
if not _secrets_path.exists():
    print(f"エラー: {_secrets_path} が見つかりません。")
    sys.exit(1)
with open(_secrets_path, "rb") as _f:
    _secrets = tomllib.load(_f)

PHRASES_FILE = BASE_DIR / "plans" / "phase25_phrases.txt"
DICT_FILE = BASE_DIR / "dialect_dict.txt"
MODEL = "gpt-5.4-mini"

PATTERN_A_PROMPT = """\
あなたは妙高市で生まれ育った在住の60代女性のアシスタントです。
観光客や地域の方の質問に答えたり、気軽に会話します。
妙高市の方言で答えてください。

### 辞書 ###
{dict_content}"""

PATTERN_B_STEP1_PROMPT = """\
あなたは妙高市で生まれ育った在住の60代女性のアシスタントです。
観光客や地域の方の質問に答えたり、気軽に会話します。
方言は使わず、標準語で簡潔に答えてください。"""

PATTERN_B_STEP2_PROMPT = """\
あなたは、標準語を妙高市の方言に翻訳するシステムです。
入力された標準語テキストを妙高市の方言に翻訳してください。
翻訳結果のみを出力し、説明は不要です。

### 辞書 ###
{dict_content}"""


def load_phrases():
    phrases = []
    with open(PHRASES_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("- "):
                phrases.append(line[2:])
            elif line:
                phrases.append(line)
    return phrases


def resolve_result_file():
    n = 1
    while True:
        path = BASE_DIR / "plans" / f"phase25_result_run{n}.md"
        if not path.exists() or not path.read_text(encoding="utf-8").strip():
            return path, n
        n += 1


def run_pattern_a(client, phrases, dict_content):
    prompt = PATTERN_A_PROMPT.format(dict_content=dict_content)
    results = []
    for i, phrase in enumerate(phrases, 1):
        response = client.responses.create(
            model=MODEL,
            instructions=prompt,
            input=phrase,
            max_output_tokens=300,
        )
        r = {
            "question": phrase,
            "dialect_answer": response.output_text.strip(),
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.total_tokens,
            "cached_tokens": response.usage.input_tokens_details.cached_tokens,
        }
        results.append(r)
        print(
            f"[A] {i}/{len(phrases)} "
            f"入力:{r['input_tokens']}(キャッシュ:{r['cached_tokens']}) "
            f"出力:{r['output_tokens']}"
        )
        print(f"  Q: {phrase}")
        print(f"  A: {r['dialect_answer']}")
    return results


def run_pattern_b(client, phrases, dict_content):
    step2_prompt = PATTERN_B_STEP2_PROMPT.format(dict_content=dict_content)
    results = []
    for i, phrase in enumerate(phrases, 1):
        # Step1: 標準語で回答
        resp1 = client.responses.create(
            model=MODEL,
            instructions=PATTERN_B_STEP1_PROMPT,
            input=phrase,
            max_output_tokens=300,
        )
        standard_answer = resp1.output_text.strip()

        # Step2: 標準語回答を方言に変換（元の質問も渡して文脈を保持）
        step2_input = f"【元の質問】{phrase}\n【標準語回答】{standard_answer}"
        resp2 = client.responses.create(
            model=MODEL,
            instructions=step2_prompt,
            input=step2_input,
            max_output_tokens=300,
        )
        dialect_answer = resp2.output_text.strip()

        total_input = resp1.usage.input_tokens + resp2.usage.input_tokens
        total_output = resp1.usage.output_tokens + resp2.usage.output_tokens
        total = resp1.usage.total_tokens + resp2.usage.total_tokens
        cached = (
            resp1.usage.input_tokens_details.cached_tokens
            + resp2.usage.input_tokens_details.cached_tokens
        )
        r = {
            "question": phrase,
            "standard_answer": standard_answer,
            "dialect_answer": dialect_answer,
            "input_tokens": total_input,
            "output_tokens": total_output,
            "total_tokens": total,
            "cached_tokens": cached,
            "step1_input": resp1.usage.input_tokens,
            "step1_output": resp1.usage.output_tokens,
            "step2_input": resp2.usage.input_tokens,
            "step2_output": resp2.usage.output_tokens,
            "step2_cached": resp2.usage.input_tokens_details.cached_tokens,
        }
        results.append(r)
        print(
            f"[B] {i}/{len(phrases)} "
            f"Step1 入力:{resp1.usage.input_tokens} 出力:{resp1.usage.output_tokens} / "
            f"Step2 入力:{resp2.usage.input_tokens}(キャッシュ:{r['step2_cached']}) "
            f"出力:{resp2.usage.output_tokens}"
        )
        print(f"  Q:      {phrase}")
        print(f"  標準語: {standard_answer}")
        print(f"  方言:   {dialect_answer}")
    return results


def format_pattern_a(results):
    lines = ["## パターンA: 標準語質問 → 方言回答（直接）", ""]
    lines.append(
        "| # | 標準語の質問 | 方言の回答 | 入力Token | キャッシュToken | キャッシュ率 | 出力Token | 合計Token |"
    )
    lines.append(
        "|---|------------|------------|-----------|----------------|------------|-----------|-----------|"
    )
    t_in = t_out = t_total = t_cached = 0
    for i, r in enumerate(results, 1):
        rate = r["cached_tokens"] / r["input_tokens"] * 100 if r["input_tokens"] else 0
        lines.append(
            f"| {i} | {r['question']} | {r['dialect_answer']} "
            f"| {r['input_tokens']} | {r['cached_tokens']} | {rate:.1f}% "
            f"| {r['output_tokens']} | {r['total_tokens']} |"
        )
        t_in += r["input_tokens"]
        t_out += r["output_tokens"]
        t_total += r["total_tokens"]
        t_cached += r["cached_tokens"]
    overall_rate = t_cached / t_in * 100 if t_in else 0
    lines.append(
        f"| **合計** | | | {t_in:,} | {t_cached:,} | {overall_rate:.1f}% | {t_out:,} | {t_total:,} |"
    )
    lines.append("")
    return "\n".join(lines), t_in, t_out, t_total, t_cached


def format_pattern_b(results):
    lines = ["## パターンB: 標準語質問 → 標準語回答 → 方言回答（2段階）", ""]
    lines.append(
        "| # | 標準語の質問 | 標準語の回答 | 方言の回答 | 入力Token合計 | キャッシュToken | キャッシュ率 | 出力Token合計 | 合計Token |"
    )
    lines.append(
        "|---|------------|------------|------------|--------------|----------------|------------|--------------|-----------|"
    )
    t_in = t_out = t_total = t_cached = 0
    for i, r in enumerate(results, 1):
        rate = r["cached_tokens"] / r["input_tokens"] * 100 if r["input_tokens"] else 0
        lines.append(
            f"| {i} | {r['question']} | {r['standard_answer']} | {r['dialect_answer']} "
            f"| {r['input_tokens']} | {r['cached_tokens']} | {rate:.1f}% "
            f"| {r['output_tokens']} | {r['total_tokens']} |"
        )
        t_in += r["input_tokens"]
        t_out += r["output_tokens"]
        t_total += r["total_tokens"]
        t_cached += r["cached_tokens"]
    overall_rate = t_cached / t_in * 100 if t_in else 0
    lines.append(
        f"| **合計** | | | | {t_in:,} | {t_cached:,} | {overall_rate:.1f}% | {t_out:,} | {t_total:,} |"
    )
    lines.append("")
    return "\n".join(lines), t_in, t_out, t_total, t_cached


def main():
    api_key = _secrets.get("OPENAI_API_KEY")
    if not api_key:
        print("エラー: OPENAI_API_KEY が設定されていません。")
        sys.exit(1)

    client = OpenAI(api_key=api_key)
    phrases = load_phrases()
    print(f"フレーズ数: {len(phrases)}\n")

    dict_content = DICT_FILE.read_text(encoding="utf-8")
    result_file, run_num = resolve_result_file()
    print(f"結果ファイル: {result_file} (Run {run_num})\n")

    print("=== パターンA: 直接方言回答 ===")
    a_results = run_pattern_a(client, phrases, dict_content)

    print("\n=== パターンB: 2段階（標準語→方言変換）===")
    b_results = run_pattern_b(client, phrases, dict_content)

    a_section, a_in, a_out, a_total, a_cached = format_pattern_a(a_results)
    b_section, b_in, b_out, b_total, b_cached = format_pattern_b(b_results)

    a_rate = a_cached / a_in * 100 if a_in else 0
    b_rate = b_cached / b_in * 100 if b_in else 0

    output = f"# フェーズ2.5 実験結果 Run{run_num}\n\n"
    output += a_section + "\n"
    output += b_section + "\n"
    output += "## 比較サマリー\n\n"
    output += "| 指標 | パターンA（直接） | パターンB（2段階） | 差分 |\n"
    output += "|------|------------------|-------------------|------|\n"
    output += f"| 合計入力Token | {a_in:,} | {b_in:,} | {b_in - a_in:+,} |\n"
    output += f"| キャッシュToken合計 | {a_cached:,} | {b_cached:,} | {b_cached - a_cached:+,} |\n"
    output += f"| キャッシュ率 | {a_rate:.1f}% | {b_rate:.1f}% | — |\n"
    output += f"| 合計出力Token | {a_out:,} | {b_out:,} | {b_out - a_out:+,} |\n"
    output += f"| 合計Token | {a_total:,} | {b_total:,} | {b_total - a_total:+,} |\n"

    result_file.write_text(output, encoding="utf-8")
    print(f"\n結果を保存しました: {result_file}")


if __name__ == "__main__":
    main()
