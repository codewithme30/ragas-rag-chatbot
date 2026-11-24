"""Loads the golden dataset and the bad-bot cases, and gives test files tiny helpers.
Why it exists: each test file can say `GOLDEN`, `ids(GOLDEN)` and `full_reference(item)`
instead of repeating file-reading code.
"""
import json

from framework.config import ROOT


def _load(name: str) -> list[dict]:
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


GOLDEN = _load("golden_dataset.json")
BAD_CASES = _load("bad_bot_cases.json")
ANSWERABLE = [g for g in GOLDEN if g["answerable"]]   # the answer exists in the HR documents
SHORT = [g for g in GOLDEN if g.get("short_answer")]  # references like "15 days" (Exact Match)


def ids(items: list[dict]) -> list[str]:
    """Use each item's `id` as the pytest test ID, so every question is its own pass/fail line."""
    return [item["id"] for item in items]


def full_reference(item: dict) -> str:
    """The ideal answer as a full sentence. Short items keep "15 days" in `reference` for Exact Match,
    but LLM judges need a sentence to break into claims."""
    return item.get("full_reference", item["reference"])
