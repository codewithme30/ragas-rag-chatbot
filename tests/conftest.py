"""Shared pytest set-up: fetches bot answers once, skips politely without an API key,
and feeds each test's score into the reports. Why it exists: so test files stay tiny.
"""
import html
from concurrent.futures import ThreadPoolExecutor

import pytest
from pytest_html import extras

from framework import results
from framework.config import CONFIG, has_api_key, metric_cfg
from framework.datasets import ANSWERABLE, GOLDEN, SHORT


def pytest_configure(config):
    config.addinivalue_line("markers", "no_key: runs without an Anthropic API key (embeddings / free metrics only)")


def pytest_sessionstart(session):
    results.start_run()  # wipe last run's results; reports are rebuilt from this run only


def pytest_sessionfinish(session, exitstatus):
    from framework.reports import build_all
    build_all()


NO_KEY_MESSAGE = "No ANTHROPIC_API_KEY found. Copy .env.example to .env and add your key to run this test."


@pytest.fixture(autouse=True)
def skip_without_api_key(request):
    """No ANTHROPIC_API_KEY? Skip (with a friendly reason) every test that needs Claude."""
    if not has_api_key() and "no_key" not in request.keywords:
        pytest.skip(NO_KEY_MESSAGE)


def _ask_all(items: list[dict], short: bool) -> dict:
    if not has_api_key():  # session fixtures run before the autouse skip above, so check here too
        pytest.skip(NO_KEY_MESSAGE)
    from chatbot.rag_bot import ask, chunk_vectors
    chunk_vectors()  # load the embedding model once, before the worker threads start
    with ThreadPoolExecutor(max_workers=CONFIG["ragas"]["max_workers"]) as pool:
        answers = list(pool.map(lambda item: ask(item["question"], short=short), items))
    return {item["id"]: answer for item, answer in zip(items, answers)}


@pytest.fixture(scope="session")
def bot_responses() -> dict:
    """{question_id: {"answer": ..., "contexts": [...]}} for every golden question (fetched once)."""
    return _ask_all(GOLDEN, short=False)


@pytest.fixture(scope="session")
def short_bot_responses() -> dict:
    """Same, but the bot is told to reply with ONLY the value (e.g. "15 days"). Used by Exact Match."""
    return _ask_all(SHORT, short=True)


@pytest.fixture
def record(request):
    """record(metric, test_id, score, question, answer, contexts, reference) saves the score for the
    reports and remembers it so the pytest-html report can show it next to this test."""
    def _record(metric, test_id, score, question, answer, contexts, reference, kind="quality", note=""):
        row = results.add_result(metric, test_id, score, question, answer, contexts, reference, kind, note)
        request.node.user_properties.append(("row", row))
        return row
    return _record


# ---- pytest-html: add Score / Threshold columns and a detail box for every scored test ----
def pytest_html_results_table_header(cells):
    cells.insert(2, "<th>Score</th>")
    cells.insert(3, "<th>Pass line</th>")


def pytest_html_results_table_row(report, cells):
    row = getattr(report, "score_row", None)
    cfg = metric_cfg(row["metric"]) if row else None
    sign = "&le;" if cfg and cfg["direction"] == "lower_is_better" else "&ge;"
    cells.insert(2, f"<td>{row['score']:.2f}</td>" if row else "<td>-</td>")
    cells.insert(3, f"<td>{sign} {cfg['threshold']:.2f}</td>" if row else "<td>-</td>")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    row = dict(item.user_properties).get("row")
    if report.when == "call" and row:
        report.score_row = row
        e = html.escape
        contexts = "".join(f"<li>{e(c)}</li>" for c in row["contexts"])
        box = (f"<div><b>Question:</b> {e(row['question'])}<br><b>Bot answer:</b> {e(row['answer'])}<br>"
               f"<b>Approved answer:</b> {e(row['reference'])}<br><b>Retrieved contexts:</b><ol>{contexts}</ol></div>")
        report.extras = getattr(report, "extras", []) + [extras.html(box)]
