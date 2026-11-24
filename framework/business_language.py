"""Turns failed scores into plain-English business impact, using fixed templates.
Why it exists: managers do not read test IDs. They want to know what went wrong, why it
matters and who should fix it. No LLM is used here, so the wording is predictable.
"""
from framework.config import metric_cfg


def excerpt(text: str, limit: int = 160) -> str:
    """Shorten long text so the report stays readable."""
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit].rstrip() + "..."


def explain_failure(row: dict) -> dict:
    """One failed quality row -> a dict of plain-English fields for the reports."""
    cfg = metric_cfg(row["metric"])
    bound = "at most" if cfg["direction"] == "lower_is_better" else "at least"
    return {
        "check": cfg["plain_name"],
        "what_happened": cfg["failure_template"],
        "score_text": f"scored {row['score']:.2f} (needs {bound} {cfg['threshold']:.2f})",
        "question": row["question"],
        "bot_said": excerpt(row["answer"]),
        "policy_says": excerpt(row["reference"]),
        "why_it_matters": cfg["business_risk_if_low"],
        "owner": cfg["likely_owner"],
    }


def counts_toward_status(row: dict) -> bool:
    """Quality rows count, except 'informational' metrics (BLEU/ROUGE/String Similarity are too weak
    for chatbot answers to decide the traffic light)."""
    return row["kind"] == "quality" and not metric_cfg(row["metric"]).get("informational", False)


def group_failures_by_risk(rows: list[dict]) -> dict[str, list[dict]]:
    """{business risk sentence: [failure dicts]}, most serious risk first (severity in config.yaml)."""
    groups: dict[str, list[dict]] = {}
    severity: dict[str, int] = {}
    for row in rows:
        if counts_toward_status(row) and not row["ok"]:
            risk = metric_cfg(row["metric"])["business_risk_if_low"]
            groups.setdefault(risk, []).append(explain_failure(row))
            severity[risk] = min(severity.get(risk, 9), metric_cfg(row["metric"])["severity"])
    return dict(sorted(groups.items(), key=lambda item: (severity[item[0]], -len(item[1]))))


def biggest_risk(rows: list[dict]) -> str:
    """The single most important sentence for the top of the email."""
    groups = group_failures_by_risk(rows)
    if not groups:
        return "No quality checks failed in this run."
    risk, items = next(iter(groups.items()))
    return f"{risk} ({len(items)} failed check{'s' if len(items) != 1 else ''})"


def traffic_light(pass_rate: float) -> tuple[str, str]:
    """(label, colour): Green >= 90% of checks passed, Amber >= 70%, otherwise Red."""
    if pass_rate >= 0.90:
        return "GREEN", "#2e7d32"
    if pass_rate >= 0.70:
        return "AMBER", "#f9a825"
    return "RED", "#c62828"


def failure_message(metric: str, score: float) -> str:
    """The sentence shown when a test fails, e.g.
    'Sticks to the facts 0.42 < 0.80: The answer contains claims that are not in the HR documents.'"""
    cfg = metric_cfg(metric)
    sign = ">" if cfg["direction"] == "lower_is_better" else "<"
    return f"{cfg['plain_name']} {score:.2f} {sign} {cfg['threshold']:.2f}: {cfg['failure_template']}"
