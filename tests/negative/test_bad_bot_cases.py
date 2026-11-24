"""Safety-net tests: feed each metric a deliberately BAD answer and check that it raises the alarm.
These tests PASS when the metric catches the problem (score on the wrong side of the pass line).
If one of these ever fails, the metric has gone blind and we would not notice real bugs.
"""
import pytest
from ragas.metrics.collections import (AnswerRelevancy, ContextPrecisionWithReference, ContextRecall,
                                       FactualCorrectness, Faithfulness, NoiseSensitivity, SemanticSimilarity)

from framework.config import metric_cfg, passes
from framework.datasets import BAD_CASES, ids
from framework.judge import judge_embeddings, judge_llm
from framework.scoring import make_sample, score

pytestmark = pytest.mark.negative


def build_metric(name: str):
    """Create the Ragas metric a bad case is aimed at."""
    llm = judge_llm()
    return {
        "faithfulness": lambda: Faithfulness(llm=llm),
        "context_recall": lambda: ContextRecall(llm=llm),
        "context_precision": lambda: ContextPrecisionWithReference(llm=llm),
        "answer_relevancy": lambda: AnswerRelevancy(llm=llm, embeddings=judge_embeddings(), strictness=1),
        "factual_correctness": lambda: FactualCorrectness(llm=llm),
        "noise_sensitivity": lambda: NoiseSensitivity(llm=llm, mode="irrelevant"),
    }[name]()


@pytest.mark.parametrize("case", BAD_CASES, ids=ids(BAD_CASES))
def test_metric_catches_bad_answer(case, record):
    metric_name = case["target_metric"]
    sample = make_sample(case["question"], case["answer"], case["contexts"], case["reference"])
    value = score(build_metric(metric_name), sample)
    row = record(metric_name, case["id"], value, case["question"], case["answer"], case["contexts"],
                 case["reference"], kind="negative", note=case["kind"])
    cfg = metric_cfg(metric_name)
    assert row["ok"], (f"Safety net MISSED '{case['kind']}': {cfg['plain_name']} scored {value:.2f}, "
                       f"which still passes the {cfg['threshold']:.2f} line. {case['what_is_wrong']}")


@pytest.mark.no_key  # Free: uses only the local embeddings model, so it also runs without an API key.
def test_semantic_similarity_catches_off_topic_answer_for_free(record):
    case = next(c for c in BAD_CASES if c["id"] == "off_topic_answer")
    sample = make_sample(case["question"], case["answer"], case["contexts"], case["reference"])
    value = score(SemanticSimilarity(embeddings=judge_embeddings()), sample)
    row = record("semantic_similarity", "off_topic_answer_free", value, case["question"], case["answer"],
                 case["contexts"], case["reference"], kind="negative", note="Off-topic answer (free check)")
    assert row["ok"], f"Safety net MISSED the off-topic answer: similarity {value:.2f} still passes. {case['what_is_wrong']}"
