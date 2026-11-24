"""Context Recall: did retrieval find ALL the facts needed to give the approved answer?
Why it matters: if the key policy was never retrieved, the bot has to guess.
"""
import pytest
from ragas.metrics.collections import ContextRecall

from framework.business_language import failure_message
from framework.config import passes
from framework.datasets import ANSWERABLE, full_reference, ids
from framework.judge import judge_llm
from framework.scoring import make_sample, score

pytestmark = pytest.mark.retrieval
METRIC = "context_recall"


@pytest.mark.parametrize("item", ANSWERABLE, ids=ids(ANSWERABLE))
def test_context_recall(item, bot_responses, record):
    bot = bot_responses[item["id"]]                                                        # 1. bot response (cached)
    sample = make_sample(item["question"], bot["answer"], bot["contexts"], full_reference(item))  # 2. build sample
    value = score(ContextRecall(llm=judge_llm()), sample)                                  # 3. score it
    record(METRIC, item["id"], value, item["question"], bot["answer"], bot["contexts"], full_reference(item))  # 4. record
    assert passes(METRIC, value), failure_message(METRIC, value)                           # 5. assert vs threshold
