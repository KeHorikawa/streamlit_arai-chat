import sys
import tomli as tomllib
from pathlib import Path
from openai import OpenAI

BASE_DIR = Path(__file__).parent.parent.parent
_secrets_path = BASE_DIR / ".streamlit" / "secrets.toml"
if not _secrets_path.exists():
    print(f"エラー: {_secrets_path} が見つかりません。")
    sys.exit(1)
with open(_secrets_path, "rb") as _f:
    _secrets = tomllib.load(_f)

PHRASES_FILE = BASE_DIR / "experiment" / "phase2" / "phrases.txt"
OLD_DICT_FILE = BASE_DIR / "dialect_dict_old.txt"
NEW_DICT_FILE = BASE_DIR / "dialect_dict.txt"
RESULT_FILE = BASE_DIR / "experiment" / "phase2" / "result.md"

MODEL = "gpt-5.4-mini"

TRANSLATION_PROMPT_TEMPLATE = """\
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


def load_dict(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def run_experiment(client, phrases, dict_content, label):
    system_prompt = TRANSLATION_PROMPT_TEMPLATE.format(dict_content=dict_content)
    results = []
    for i, phrase in enumerate(phrases, 1):
        response = client.responses.create(
            model=MODEL,
            instructions=system_prompt,
            input=phrase,
            max_output_tokens=200,
        )
        result = {
            "phrase": phrase,
            "translation": response.output_text.strip(),
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.total_tokens,
            "cached_tokens": response.usage.input_tokens_details.cached_tokens,
        }
        results.append(result)
        print(
            f"[{label}] {i}/{len(phrases)} "
            f"入力:{result['input_tokens']}(キャッシュ:{result['cached_tokens']}) "
            f"出力:{result['output_tokens']}"
        )
        print(f"  {phrase}")
        print(f"  → {result['translation']}")
    return results


def format_table(label, results):
    lines = [f"## {label}", ""]
    lines.append("| # | 標準語 | 翻訳結果 | 入力Token | キャッシュToken | キャッシュ率 | 出力Token | 合計Token |")
    lines.append("|---|--------|----------|-----------|----------------|------------|-----------|-----------|")
    total_input = total_output = total = total_cached = 0
    for i, r in enumerate(results, 1):
        cache_rate = r["cached_tokens"] / r["input_tokens"] * 100 if r["input_tokens"] else 0
        lines.append(
            f"| {i} | {r['phrase']} | {r['translation']} "
            f"| {r['input_tokens']} | {r['cached_tokens']} | {cache_rate:.1f}% "
            f"| {r['output_tokens']} | {r['total_tokens']} |"
        )
        total_input += r["input_tokens"]
        total_output += r["output_tokens"]
        total += r["total_tokens"]
        total_cached += r["cached_tokens"]
    overall_rate = total_cached / total_input * 100 if total_input else 0
    lines.append(
        f"| **合計** | | | {total_input:,} | {total_cached:,} | {overall_rate:.1f}% | {total_output:,} | {total:,} |"
    )
    lines.append("")
    return "\n".join(lines), total_input, total_output, total, total_cached


def main():
    api_key = _secrets.get("OPENAI_API_KEY")
    if not api_key:
        print("エラー: OPENAI_API_KEY が設定されていません。.streamlit/secrets.toml を確認してください。")
        sys.exit(1)

    client = OpenAI(api_key=api_key)
    phrases = load_phrases()
    print(f"フレーズ数: {len(phrases)}\n")

    has_old_backup = OLD_DICT_FILE.exists()
    has_current = NEW_DICT_FILE.exists()

    if not has_current:
        print(f"エラー: 辞書ファイルが見つかりません: {NEW_DICT_FILE}")
        sys.exit(1)

    sections = []

    if has_old_backup:
        # フェーズ2: 旧辞書（バックアップ）と新辞書を比較
        print("=== 旧辞書で実験中 ===")
        old_results = run_experiment(client, phrases, load_dict(OLD_DICT_FILE), "旧辞書")
        sections.append(("旧辞書", *format_table("旧辞書", old_results)))

        print("\n=== 新辞書で実験中 ===")
        new_results = run_experiment(client, phrases, load_dict(NEW_DICT_FILE), "新辞書")
        sections.append(("新辞書", *format_table("新辞書", new_results)))
    else:
        # フェーズ1: 現在の辞書のみ（旧辞書として記録）
        print("=== 旧辞書で実験中 ===")
        old_results = run_experiment(client, phrases, load_dict(NEW_DICT_FILE), "旧辞書")
        sections.append(("旧辞書", *format_table("旧辞書", old_results)))

    # 結果ファイルの組み立て
    output = "# 実験結果\n\n"
    for name, section, *_ in sections:
        output += section + "\n"

    if len(sections) == 2:
        _, _, old_in, old_out, old_total, old_cached = sections[0]
        _, _, new_in, new_out, new_total, new_cached = sections[1]
        old_rate = old_cached / old_in * 100 if old_in else 0
        new_rate = new_cached / new_in * 100 if new_in else 0
        output += "## 比較サマリー\n\n"
        output += "| 指標 | 旧辞書 | 新辞書 | 差分 |\n"
        output += "|------|--------|--------|------|\n"
        output += f"| 合計入力Token | {old_in:,} | {new_in:,} | {new_in - old_in:+,} |\n"
        output += f"| キャッシュToken合計 | {old_cached:,} | {new_cached:,} | {new_cached - old_cached:+,} |\n"
        output += f"| キャッシュ率 | {old_rate:.1f}% | {new_rate:.1f}% | — |\n"
        output += f"| 合計出力Token | {old_out:,} | {new_out:,} | {new_out - old_out:+,} |\n"
        output += f"| 合計Token | {old_total:,} | {new_total:,} | {new_total - old_total:+,} |\n"

    RESULT_FILE.write_text(output, encoding="utf-8")
    print(f"\n結果を保存しました: {RESULT_FILE}")


if __name__ == "__main__":
    main()
