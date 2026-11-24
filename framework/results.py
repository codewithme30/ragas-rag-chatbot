"""Collects every score produced during a test run into reports/results.jsonl.
Why it exists: the reports (CSV, chart, email...) are built from this one file, so
they can be rebuilt any time with `make report` without re-running the tests.
"""
import json
from datetime import datetime

from framework.config import CONFIG, REPORTS_DIR, bot_mode, passes

RESULTS_FILE = REPORTS_DIR / "results.jsonl"
META_FILE = REPORTS_DIR / "run_meta.json"


def start_run() -> None:
    """Called once at the start of a pytest session: wipe old results, save run details."""
    REPORTS_DIR.mkdir(exist_ok=True)
    RESULTS_FILE.write_text("", encoding="utf-8")
    meta = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "bot_mode": bot_mode(),
        "bot_llm": CONFIG["models"]["bot_llm"],
        "judge_llm": CONFIG["models"]["judge_llm"],
    }
    META_FILE.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def add_result(metric: str, test_id: str, score: float, question: str, answer: str,
               contexts: list[str], reference: str, kind: str = "quality", note: str = "") -> dict:
    """Save one score. kind='quality' for normal tests, 'negative' for the safety-net tests.
    For quality rows `ok` = the bot passed. For negative rows `ok` = the metric CAUGHT the bad answer."""
    metric_passes = passes(metric, score)
    row = {
        "metric": metric, "test_id": test_id, "kind": kind,
        "score": round(float(score), 3), "ok": metric_passes if kind == "quality" else not metric_passes,
        "question": question, "answer": answer, "contexts": contexts, "reference": reference, "note": note,
    }
    with open(RESULTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return row


def load_results() -> list[dict]:
    if not RESULTS_FILE.exists():
        return []
    lines = RESULTS_FILE.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def load_meta() -> dict:
    if META_FILE.exists():
        return json.loads(META_FILE.read_text(encoding="utf-8"))
    return {"date": "unknown", "bot_mode": "unknown", "bot_llm": "?", "judge_llm": "?"}
