"""Noise Sensitivity: when an IRRELEVANT page sneaks into retrieval, does the answer wrongly use it?
LOWER IS BETTER here: 0.0 is perfect, and the threshold in config.yaml is a MAXIMUM.
"""
import pytest
from ragas.metrics.collections import NoiseSensitivity

from framework.business_language import failure_message
from framework.config import passes
from framework.datasets import ANSWERABLE, full_reference, ids
from framework.judge import judge_llm
from framework.scoring import make_sample, score

pytestmark = pytest.mark.answer_quality
METRIC = "noise_sensitivity"


@pytest.mark.parametrize("item", ANSWERABLE, ids=ids(ANSWERABLE))
def test_noise_sensitivity(item, bot_responses, record):
    bot = bot_responses[item["id"]]                                                        # 1. bot response (cached)
    sample = make_sample(item["question"], bot["answer"], bot["contexts"], full_reference(item))  # 2. build sample
    # mode="irrelevant": count wrong claims that came from pages that don't help answer the question.
    value = score(NoiseSensitivity(llm=judge_llm(), mode="irrelevant"), sample)            # 3. score it
    record(METRIC, item["id"], value, item["question"], bot["answer"], bot["contexts"], full_reference(item))  # 4. record
    assert passes(METRIC, value), failure_message(METRIC, value)  # passes() knows lower is better  # 5. assert
