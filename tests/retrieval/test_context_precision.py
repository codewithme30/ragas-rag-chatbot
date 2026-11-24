"""Context Precision: of the HR pages the bot retrieved, are the useful ones ranked first?
Why it matters: junk or badly ordered pages make answers slower, costlier and less accurate.
"""
import pytest
from ragas.metrics.collections import ContextPrecisionWithReference

from framework.business_language import failure_message
from framework.datasets import ANSWERABLE, full_reference, ids
from framework.judge import judge_llm
from framework.config import passes
from framework.scoring import make_sample, score

pytestmark = pytest.mark.retrieval
METRIC = "context_precision"


@pytest.mark.parametrize("item", ANSWERABLE, ids=ids(ANSWERABLE))
def test_context_precision(item, bot_responses, record):
    bot = bot_responses[item["id"]]                                                        # 1. bot response (cached)
    sample = make_sample(item["question"], bot["answer"], bot["contexts"], full_reference(item))  # 2. build sample
    value = score(ContextPrecisionWithReference(llm=judge_llm()), sample)                  # 3. score it
    record(METRIC, item["id"], value, item["question"], bot["answer"], bot["contexts"], full_reference(item))  # 4. record
    assert passes(METRIC, value), failure_message(METRIC, value)                           # 5. assert vs threshold
