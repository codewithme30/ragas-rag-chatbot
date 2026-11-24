"""String Similarity: how alike two texts are, letter by letter (Levenshtein edit distance).
WEAK for chatbots: it sees characters, not meaning. Great for IDs and codes, poor for sentences:
two answers that mean the same thing but are worded differently look "different".
"""
import pytest
from ragas.metrics.collections import NonLLMStringSimilarity

from framework.business_language import failure_message
from framework.config import passes
from framework.datasets import GOLDEN, full_reference, ids
from framework.scoring import make_sample, score

pytestmark = pytest.mark.non_llm
METRIC = "string_similarity"


@pytest.mark.parametrize("item", GOLDEN, ids=ids(GOLDEN))
def test_string_similarity(item, bot_responses, record):
    bot = bot_responses[item["id"]]                                                        # 1. bot response (cached)
    sample = make_sample(item["question"], bot["answer"], bot["contexts"], full_reference(item))  # 2. build sample
    value = score(NonLLMStringSimilarity(), sample)                                        # 3. score it
    record(METRIC, item["id"], value, item["question"], bot["answer"], bot["contexts"], full_reference(item))  # 4. record
    assert passes(METRIC, value), failure_message(METRIC, value)                           # 5. assert vs threshold
