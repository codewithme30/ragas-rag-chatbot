"""Semantic Similarity: does the answer MEAN the same as the approved answer, even in other words?
Uses only the local embeddings model (no judge LLM call), so it is cheap.
"""
import pytest
from ragas.metrics.collections import SemanticSimilarity

from framework.business_language import failure_message
from framework.config import passes
from framework.datasets import GOLDEN, full_reference, ids
from framework.judge import judge_embeddings
from framework.scoring import make_sample, score

pytestmark = pytest.mark.answer_quality
METRIC = "semantic_similarity"


@pytest.mark.parametrize("item", GOLDEN, ids=ids(GOLDEN))
def test_semantic_similarity(item, bot_responses, record):
    bot = bot_responses[item["id"]]                                                        # 1. bot response (cached)
    sample = make_sample(item["question"], bot["answer"], bot["contexts"], full_reference(item))  # 2. build sample
    value = score(SemanticSimilarity(embeddings=judge_embeddings()), sample)               # 3. score it
    record(METRIC, item["id"], value, item["question"], bot["answer"], bot["contexts"], full_reference(item))  # 4. record
    assert passes(METRIC, value), failure_message(METRIC, value)                           # 5. assert vs threshold
