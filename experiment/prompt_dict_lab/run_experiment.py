"""プロンプト・辞書 改善実験ハーネス（汎用）

config.toml に定義した「アーム（プロンプト×辞書の組み合わせ）」を
同じフレーズ集に対して実行し、出力と消費トークンを横並びで比較する。

使い方:
    python experiment/prompt_dict_lab/run_experiment.py
    python experiment/prompt_dict_lab/run_experiment.py --config config.toml

設計方針:
- プロンプトと辞書は variants/ 配下のテキストファイルとして外出しし、
  config.toml で参照だけ差し替える（コードは触らない）。
- 結果は results/ に Run番号つきで追記されないよう新規ファイルとして保存。
- 今回限りでなく、今後のプロンプト・辞書改善でも使い回せる構成にする。
"""

import argparse
import sys
from pathlib import Path

import tomli as tomllib
from openai import OpenAI

LAB_DIR = Path(__file__).parent
BASE_DIR = LAB_DIR.parent.parent


def load_secrets():
    secrets_path = BASE_DIR / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        sys.exit(f"エラー: {secrets_path} が見つかりません。")
    with open(secrets_path, "rb") as f:
        secrets = tomllib.load(f)
    api_key = secrets.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("エラー: OPENAI_API_KEY が設定されていません。")
    return api_key


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        sys.exit(f"エラー: 設定ファイルが見つかりません: {config_path}")
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def resolve(rel_path: str) -> Path:
    """config 内の相対パスを lab ディレクトリ基準で解決する。"""
    return (LAB_DIR / rel_path).resolve()


def load_phrases(path: Path) -> list[str]:
    phrases = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            phrases.append(line[2:] if line.startswith("- ") else line)
    return phrases


def build_instructions(prompt_template: str, dict_content: str) -> str:
    """プロンプトに {dict_content} があれば辞書を差し込む。無ければそのまま。"""
    if "{dict_content}" in prompt_template:
        return prompt_template.format(dict_content=dict_content)
    return prompt_template


def run_arm(client, model, arm, phrases, max_output_tokens):
    prompt_template = resolve(arm["prompt"]).read_text(encoding="utf-8")
    dict_content = resolve(arm["dict"]).read_text(encoding="utf-8") if arm.get("dict") else ""
    instructions = build_instructions(prompt_template, dict_content)

    results = []
    for i, phrase in enumerate(phrases, 1):
        response = client.responses.create(
            model=model,
            instructions=instructions,
            input=phrase,
            max_output_tokens=max_output_tokens,
        )
        r = {
            "phrase": phrase,
            "output": response.output_text.strip(),
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.total_tokens,
            "cached_tokens": response.usage.input_tokens_details.cached_tokens,
        }
        results.append(r)
        print(
            f"[{arm['name']}] {i}/{len(phrases)} "
            f"入力:{r['input_tokens']}(キャッシュ:{r['cached_tokens']}) 出力:{r['output_tokens']}"
        )
        print(f"  Q: {phrase}")
        print(f"  A: {r['output']}")
    return results


def totals(results):
    t_in = sum(r["input_tokens"] for r in results)
    t_out = sum(r["output_tokens"] for r in results)
    t_total = sum(r["total_tokens"] for r in results)
    t_cached = sum(r["cached_tokens"] for r in results)
    return t_in, t_out, t_total, t_cached


def format_arm_table(arm_name, results):
    lines = [f"### アーム: {arm_name}", ""]
    lines.append("| # | 入力（標準語） | 出力（方言） | 入力Tok | キャッシュ | 出力Tok | 合計Tok |")
    lines.append("|---|----------------|--------------|---------|-----------|---------|---------|")
    for i, r in enumerate(results, 1):
        lines.append(
            f"| {i} | {r['phrase']} | {r['output']} "
            f"| {r['input_tokens']} | {r['cached_tokens']} | {r['output_tokens']} | {r['total_tokens']} |"
        )
    t_in, t_out, t_total, t_cached = totals(results)
    lines.append(f"| **合計** | | | {t_in:,} | {t_cached:,} | {t_out:,} | {t_total:,} |")
    lines.append("")
    return "\n".join(lines)


def format_side_by_side(arm_names, all_results, phrases):
    """同じフレーズに対する各アームの出力を横並びにした定性比較表。"""
    header = "| # | 入力 | " + " | ".join(arm_names) + " |"
    sep = "|---|------|" + "|".join(["------"] * len(arm_names)) + "|"
    lines = ["### 出力の横並び比較（定性評価用）", "", header, sep]
    for i, phrase in enumerate(phrases):
        cells = [res[i]["output"] for res in all_results]
        lines.append(f"| {i + 1} | {phrase} | " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


def format_token_summary(arm_names, all_results):
    lines = ["### トークン比較サマリー", ""]
    lines.append("| アーム | 入力Tok | キャッシュ | キャッシュ率 | 出力Tok | 合計Tok |")
    lines.append("|--------|---------|-----------|------------|---------|---------|")
    for name, results in zip(arm_names, all_results):
        t_in, t_out, t_total, t_cached = totals(results)
        rate = t_cached / t_in * 100 if t_in else 0
        lines.append(f"| {name} | {t_in:,} | {t_cached:,} | {rate:.1f}% | {t_out:,} | {t_total:,} |")
    lines.append("")
    return "\n".join(lines)


def resolve_result_file(title: str) -> Path:
    results_dir = LAB_DIR / "results"
    results_dir.mkdir(exist_ok=True)
    slug = title.replace(" ", "_")
    n = 1
    while True:
        path = results_dir / f"{slug}_run{n}.md"
        if not path.exists() or not path.read_text(encoding="utf-8").strip():
            return path
        n += 1


def main():
    parser = argparse.ArgumentParser(description="プロンプト・辞書 改善実験ハーネス")
    parser.add_argument("--config", default="config.toml", help="設定ファイル（lab基準の相対パス）")
    args = parser.parse_args()

    config = load_config(resolve(args.config))
    title = config.get("title", "experiment")
    model = config.get("model", "gpt-5.4-mini")
    max_output_tokens = config.get("max_output_tokens", 300)
    arms = config.get("arms", [])
    if not arms:
        sys.exit("エラー: config.toml に [[arms]] が定義されていません。")

    phrases = load_phrases(resolve(config["phrases"]))
    print(f"実験: {title}")
    print(f"モデル: {model} / フレーズ数: {len(phrases)} / アーム数: {len(arms)}\n")

    client = OpenAI(api_key=load_secrets())

    arm_names = [a["name"] for a in arms]
    all_results = []
    for arm in arms:
        print(f"=== アーム実行中: {arm['name']} ===")
        all_results.append(run_arm(client, model, arm, phrases, max_output_tokens))
        print()

    output = [f"# 実験結果: {title}", ""]
    output.append("## 設定")
    output.append("")
    output.append(f"- モデル: `{model}`")
    output.append(f"- フレーズ: `{config['phrases']}`（{len(phrases)}件）")
    for arm in arms:
        output.append(f"- アーム `{arm['name']}`: prompt=`{arm['prompt']}` / dict=`{arm.get('dict', '—')}`")
    output.append("")
    output.append("## 出力比較")
    output.append("")
    output.append(format_side_by_side(arm_names, all_results, phrases))
    output.append(format_token_summary(arm_names, all_results))
    output.append("## アーム別詳細")
    output.append("")
    for name, results in zip(arm_names, all_results):
        output.append(format_arm_table(name, results))

    result_file = resolve_result_file(title)
    result_file.write_text("\n".join(output), encoding="utf-8")
    print(f"結果を保存しました: {result_file}")


if __name__ == "__main__":
    main()
