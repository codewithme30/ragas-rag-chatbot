"""One command to run the whole demo: python run_demo.py [--buggy] [--group <marker>] [--no-cache].
Runs pytest (which builds every report when it finishes) and prints where the reports are.
Works on Windows, Mac and Linux because it only uses Python, not shell scripts.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GROUPS = ["retrieval", "generation", "answer_quality", "non_llm", "negative"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the RAG quality demo.")
    parser.add_argument("--buggy", action="store_true", help="test the deliberately broken bot (shows red results)")
    parser.add_argument("--group", choices=GROUPS, help="run only one group of tests")
    parser.add_argument("--no-cache", action="store_true", help="ignore saved bot/judge answers (costs money, slower)")
    args = parser.parse_args()

    env = dict(os.environ)
    env["BOT_MODE"] = "buggy" if args.buggy else env.get("BOT_MODE", "good")
    if args.no_cache:
        env["RAG_DEMO_NO_CACHE"] = "1"

    from dotenv import load_dotenv  # only to detect the key for the message below
    load_dotenv(ROOT / ".env")
    if not (os.environ.get("ANTHROPIC_API_KEY") or env.get("ANTHROPIC_API_KEY")):
        print("NOTE: no ANTHROPIC_API_KEY found, so tests that call Claude will be SKIPPED.")
        print("      Copy .env.example to .env and add your key to run everything.\n")

    command = [sys.executable, "-m", "pytest"] + (["-m", args.group] if args.group else [])
    print(f"Running: {' '.join(command)}   (bot mode: {env['BOT_MODE']})\n")
    code = subprocess.call(command, cwd=ROOT, env=env)

    reports = ROOT / "reports"
    print("\nReports are in:", reports)
    for name in ["email_report.html", "email_report.md", "pytest_report.html", "scores.xlsx", "scores.csv", "metric_scores.png"]:
        if (reports / name).exists():
            print(f"  - {reports / name}")
    if args.buggy and code != 0:
        print("\n(The failures above are EXPECTED: the buggy bot is broken on purpose.)")
    return code


if __name__ == "__main__":
    sys.exit(main())
