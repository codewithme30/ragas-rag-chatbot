"""Faithfulness: is every claim in the answer backed by the retrieved HR documents?
Analogy: an open-book exam where you may only quote the book. Needs no reference answer.
"""
import pytest
from ragas.metrics.collections import Faithfulness

from framework.business_language import failure_message
from framework.config import passes
from framework.datasets import ANSWERABLE, full_reference, ids
from framework.judge import judge_llm
from framework.scoring import make_sample, score

pytestmark = pytest.mark.generation
METRIC = "faithfulness"


@pytest.mark.parametrize("item", ANSWERABLE, ids=ids(ANSWERABLE))
def test_faithfulness(item, bot_responses, record):
    bot = bot_responses[item["id"]]                                                        # 1. bot response (cached)
    sample = make_sample(item["question"], bot["answer"], bot["contexts"], full_reference(item))  # 2. build sample
    value = score(Faithfulness(llm=judge_llm()), sample)                                   # 3. score it
    record(METRIC, item["id"], value, item["question"], bot["answer"], bot["contexts"], full_reference(item))  # 4. record
    assert passes(METRIC, value), failure_message(METRIC, value)                           # 5. assert vs threshold
