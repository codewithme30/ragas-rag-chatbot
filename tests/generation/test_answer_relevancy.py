"""Answer Relevancy: does the answer address the question that was asked?
Ragas guesses which question the answer would fit, then compares it to the real question
using embeddings. Needs no reference answer. (We skip the "not in the documents" question:
an honest "I don't know" is deliberately scored as non-committal by this metric.)
"""
import pytest
from ragas.metrics.collections import AnswerRelevancy

from framework.business_language import failure_message
from framework.config import passes
from framework.datasets import ANSWERABLE, full_reference, ids
from framework.judge import judge_embeddings, judge_llm
from framework.scoring import make_sample, score

pytestmark = pytest.mark.generation
METRIC = "answer_relevancy"


@pytest.mark.parametrize("item", ANSWERABLE, ids=ids(ANSWERABLE))
def test_answer_relevancy(item, bot_responses, record):
    bot = bot_responses[item["id"]]                                                        # 1. bot response (cached)
    sample = make_sample(item["question"], bot["answer"], bot["contexts"], full_reference(item))  # 2. build sample
    # Anthropic can't return n>1 answers per call. This Ragas version makes `strictness` separate
    # single calls in a loop, so it is safe; strictness=1 keeps the demo cheap.
    metric = AnswerRelevancy(llm=judge_llm(), embeddings=judge_embeddings(), strictness=1)
    value = score(metric, sample)                                                          # 3. score it
    record(METRIC, item["id"], value, item["question"], bot["answer"], bot["contexts"], full_reference(item))  # 4. record
    assert passes(METRIC, value), failure_message(METRIC, value)                           # 5. assert vs threshold
