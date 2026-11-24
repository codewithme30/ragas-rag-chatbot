"""One helper, score(metric, sample) -> float, that every test uses.
Why it exists: Ragas metrics each want slightly different inputs. This picks the right
fields out of one simple sample dict, so test files stay short and identical in shape.
"""
import inspect
import math


def make_sample(question: str, answer: str, contexts: list[str], reference: str) -> dict:
    """A 'sample' is just the four things Ragas ever needs, under Ragas's own names."""
    return {"user_input": question, "response": answer,
            "retrieved_contexts": contexts, "reference": reference}


def score(metric, sample: dict) -> float:
    """Run one Ragas metric on one sample and return a plain float (0.0 to 1.0).
    Each metric's ascore() lists the fields it accepts; we pass only those."""
    wanted = inspect.signature(metric.ascore).parameters
    inputs = {name: sample[name] for name in wanted if name in sample}
    value = metric.score(**inputs).value   # .score() is the sync wrapper around ascore()
    if value is None or math.isnan(value):
        raise ValueError(f"{metric.name} returned no score (the judge could not evaluate this sample)")
    return float(value)
