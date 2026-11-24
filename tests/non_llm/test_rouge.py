"""ROUGE-L: how much of the approved answer's wording (longest common word sequence) appears in the answer.
WEAK for chatbots: it rewards copied wording, not correct meaning. "30 days" vs "15 days" differ
by ONE word, so a wrong answer can still score high. Use it as a cheap smoke signal, never alone.
"""
import pytest
from ragas.metrics.collections import RougeScore

from framework.business_language import failure_message
from framework.config import passes
from framework.datasets import GOLDEN, full_reference, ids
from framework.scoring import make_sample, score

pytestmark = pytest.mark.non_llm
METRIC = "rouge"


@pytest.mark.parametrize("item", GOLDEN, ids=ids(GOLDEN))
def test_rouge(item, bot_responses, record):
    bot = bot_responses[item["id"]]                                                        # 1. bot response (cached)
    sample = make_sample(item["question"], bot["answer"], bot["contexts"], full_reference(item))  # 2. build sample
    value = score(RougeScore(rouge_type="rougeL", mode="fmeasure"), sample)                # 3. score it
    record(METRIC, item["id"], value, item["question"], bot["answer"], bot["contexts"], full_reference(item))  # 4. record
    assert passes(METRIC, value), failure_message(METRIC, value)                           # 5. assert vs threshold
