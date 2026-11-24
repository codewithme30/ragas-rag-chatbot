"""Loads config.yaml and .env so every other file reads settings from ONE place.
Why it exists: no model names, thresholds or paths are hard-coded anywhere else.
"""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "reports"
CACHE_DIR = ROOT / ".cache"

load_dotenv(ROOT / ".env")  # puts ANTHROPIC_API_KEY (and friends) into os.environ

with open(ROOT / "config.yaml", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)


def has_api_key() -> bool:
    """True if an Anthropic key is available. Tests use this to skip politely."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def bot_mode() -> str:
    """'good' (default) or 'buggy'. Read at call time so run_demo.py --buggy works."""
    return os.environ.get("BOT_MODE", "good").lower()


def use_cache() -> bool:
    """False when run_demo.py --no-cache sets RAG_DEMO_NO_CACHE=1."""
    return os.environ.get("RAG_DEMO_NO_CACHE") != "1"


def metric_cfg(name: str) -> dict:
    """Settings for one metric (threshold, direction, plain-English text)."""
    return CONFIG["metrics"][name]


def passes(name: str, score: float) -> bool:
    """Apply the metric's threshold in the right direction."""
    cfg = metric_cfg(name)
    if cfg["direction"] == "lower_is_better":
        return score <= cfg["threshold"]
    return score >= cfg["threshold"]
