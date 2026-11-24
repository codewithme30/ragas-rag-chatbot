"""Exact Match: 1.0 only if the answer is IDENTICAL to the expected text, otherwise 0.0.
VERY STRICT: "15 days." (with a full stop) already fails. So we only run it on the short-answer
questions, and we ask the bot to reply with ONLY the value (the `short_bot_responses` fixture).
"""
import pytest
from ragas.metrics.collections import ExactMatch

from framework.business_language import failure_message
from framework.config import passes
from framework.datasets import SHORT, ids
from framework.scoring import make_sample, score

pytestmark = pytest.mark.non_llm
METRIC = "exact_match"


@pytest.mark.parametrize("item", SHORT, ids=ids(SHORT))
def test_exact_match(item, short_bot_responses, record):
    bot = short_bot_responses[item["id"]]                                                  # 1. bot response (cached)
    sample = make_sample(item["question"], bot["answer"], bot["contexts"], item["reference"])  # 2. build sample ("15 days")
    value = score(ExactMatch(), sample)                                                    # 3. score it
    record(METRIC, item["id"], value, item["question"], bot["answer"], bot["contexts"], item["reference"])  # 4. record
    assert passes(METRIC, value), failure_message(METRIC, value)                           # 5. assert vs threshold
