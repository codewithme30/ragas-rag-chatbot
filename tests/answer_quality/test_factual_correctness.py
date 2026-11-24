"""Factual Correctness: do the facts in the answer match the approved answer?
Ragas splits both into small claims and compares them (F1). It also runs on the
"not in the documents" question: a bot that guesses there will be caught here.
"""
import pytest
from ragas.metrics.collections import FactualCorrectness

from framework.business_language import failure_message
from framework.config import passes
from framework.datasets import GOLDEN, full_reference, ids
from framework.judge import judge_llm
from framework.scoring import make_sample, score

pytestmark = pytest.mark.answer_quality
METRIC = "factual_correctness"


@pytest.mark.parametrize("item", GOLDEN, ids=ids(GOLDEN))
def test_factual_correctness(item, bot_responses, record):
    bot = bot_responses[item["id"]]                                                        # 1. bot response (cached)
    sample = make_sample(item["question"], bot["answer"], bot["contexts"], full_reference(item))  # 2. build sample
    value = score(FactualCorrectness(llm=judge_llm()), sample)                             # 3. score it
    record(METRIC, item["id"], value, item["question"], bot["answer"], bot["contexts"], full_reference(item))  # 4. record
    assert passes(METRIC, value), failure_message(METRIC, value)                           # 5. assert vs threshold
