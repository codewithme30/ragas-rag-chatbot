"""BLEU: counts matching word sequences (n-grams) between answer and approved answer.
WEAK for chatbots: it was invented for machine translation. A perfectly correct answer
in different words scores low, which is why the pass line in config.yaml is only 0.10.
Free and deterministic, but it still needs the bot's answer (so it needs the API key).
"""
import pytest
from ragas.metrics.collections import BleuScore

from framework.business_language import failure_message
from framework.config import passes
from framework.datasets import GOLDEN, full_reference, ids
from framework.scoring import make_sample, score

pytestmark = pytest.mark.non_llm
METRIC = "bleu"


@pytest.mark.parametrize("item", GOLDEN, ids=ids(GOLDEN))
def test_bleu(item, bot_responses, record):
    bot = bot_responses[item["id"]]                                                        # 1. bot response (cached)
    sample = make_sample(item["question"], bot["answer"], bot["contexts"], full_reference(item))  # 2. build sample
    value = score(BleuScore(), sample)                                                     # 3. score it
    record(METRIC, item["id"], value, item["question"], bot["answer"], bot["contexts"], full_reference(item))  # 4. record
    assert passes(METRIC, value), failure_message(METRIC, value)                           # 5. assert vs threshold
