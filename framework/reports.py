"""Builds every report from reports/results.jsonl: CSV, Excel, chart, console table,
and the emailable HTML + Markdown. Why it exists: one place turns raw scores into
something a manager can read. Run `python -m framework.reports` to rebuild without re-testing.
"""
import csv
import html

from framework.business_language import biggest_risk, counts_toward_status, group_failures_by_risk, traffic_light
from framework.config import CONFIG, REPORTS_DIR, metric_cfg, passes
from framework.results import load_meta, load_results

METRIC_ORDER = list(CONFIG["metrics"])  # same order as config.yaml
HTML_REPORT_NAME = "pytest_report.html"


# ---- Shared numbers ---------------------------------------------------------------------
def build_summary(rows: list[dict]) -> dict:
    """Everything the reports need, computed once."""
    quality = [r for r in rows if r["kind"] == "quality"]
    negatives = [r for r in rows if r["kind"] == "negative"]
    scorecard = []
    for name in METRIC_ORDER:
        mine = [r for r in quality if r["metric"] == name]
        if not mine:
            continue
        avg = sum(r["score"] for r in mine) / len(mine)
        scorecard.append({"metric": name, "avg": avg, "n": len(mine), "n_ok": sum(r["ok"] for r in mine),
                          "ok": passes(name, avg), **metric_cfg(name)})
    counted = [r for r in quality if counts_toward_status(r)]
    rate = sum(r["ok"] for r in counted) / len(counted) if counted else 0.0
    label, colour = traffic_light(rate)
    return {"meta": load_meta(), "scorecard": scorecard, "pass_rate": rate, "light": label, "colour": colour,
            "n_questions": len({r["question"] for r in quality}), "n_checks": len(counted),
            "risk": biggest_risk(rows), "groups": group_failures_by_risk(rows), "negatives": negatives}


# ---- CSV + Excel ------------------------------------------------------------------------
def write_csv_and_excel(rows: list[dict]) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    quality = [r for r in rows if r["kind"] == "quality"]
    metrics = [m for m in METRIC_ORDER if any(r["metric"] == m for r in quality)]
    ids = list(dict.fromkeys(r["test_id"] for r in quality))
    lookup = {(r["test_id"], r["metric"]): r for r in quality}
    table = [[i] + [lookup[(i, m)]["score"] if (i, m) in lookup else "" for m in metrics] for i in ids]

    with open(REPORTS_DIR / "scores.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([["question_id"] + metrics] + table)

    green, red = PatternFill("solid", fgColor="C8E6C9"), PatternFill("solid", fgColor="FFCDD2")
    wb = Workbook()
    ws = wb.active
    ws.title = "Scores"
    ws.append(["question_id"] + metrics)
    for line in table:
        ws.append(line)
    for r_idx, test_id in enumerate(ids, start=2):          # colour each cell pass / fail
        for c_idx, m in enumerate(metrics, start=2):
            if (test_id, m) in lookup:
                ws.cell(r_idx, c_idx).fill = green if lookup[(test_id, m)]["ok"] else red
    summary = wb.create_sheet("Summary")
    summary.append(["Metric", "Plain name", "Average", "Threshold", "Direction", "Checks passed", "Status"])
    for s in build_summary(rows)["scorecard"]:
        summary.append([s["metric"], s["plain_name"], round(s["avg"], 3), s["threshold"], s["direction"],
                        f"{s['n_ok']}/{s['n']}", "PASS" if s["ok"] else "FAIL"])
        summary.cell(summary.max_row, 7).fill = green if s["ok"] else red
    for sheet in (ws, summary):
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        sheet.column_dimensions["A"].width = 30
        sheet.column_dimensions["B"].width = 28
    wb.save(REPORTS_DIR / "scores.xlsx")


# ---- Chart ------------------------------------------------------------------------------
def write_chart(summary: dict) -> None:
    """Horizontal bars = average score per metric; a black tick marks each pass line.
    Failing bars are red AND labelled FAIL, so colour is never the only signal."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cards = summary["scorecard"][::-1]  # reversed so the first metric is at the top
    if not cards:
        return
    fig, ax = plt.subplots(figsize=(10, 0.6 * len(cards) + 1.8))
    for y, c in enumerate(cards):
        ax.barh(y, c["avg"], height=0.5, color="#2a6fb0" if c["ok"] else "#c62828")
        ax.plot([c["threshold"]] * 2, [y - 0.36, y + 0.36], color="black", lw=2.5)
        flag = "pass" if c["ok"] else "FAIL"
        ax.text(max(c["avg"], c["threshold"]) + 0.02, y, f"{c['avg']:.2f}  {flag}", va="center", fontsize=10)
    ax.set_yticks(range(len(cards)))
    ax.set_yticklabels([c["plain_name"] + (" (lower = better)" if c["direction"] == "lower_is_better" else "")
                        for c in cards], fontsize=10)
    ax.set_xlim(0, 1.25)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_title(f"Average score per metric   |   bot mode: {summary['meta']['bot_mode']}   |   black tick = pass line",
                 fontsize=11, loc="left")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(REPORTS_DIR / "metric_scores.png", dpi=150)
    plt.close(fig)


# ---- Console ----------------------------------------------------------------------------
def print_console_summary(summary: dict) -> None:
    print("\n" + "=" * 100)
    print(f" RAG QUALITY SUMMARY  |  bot mode: {summary['meta']['bot_mode']}  |  overall: {summary['light']}  "
          f"({summary['pass_rate']:.0%} of {summary['n_checks']} checks passed)")
    print("=" * 100)
    for s in summary["scorecard"]:
        mark = "✅" if s["ok"] else ("➖" if s.get("informational") else "❌")  # ➖ = weak metric, informational only
        print(f" {s['plain_name']:<30} {s['avg']:.2f}  {mark}  {s['question_it_answers']}")
    caught = sum(r["ok"] for r in summary["negatives"])
    if summary["negatives"]:
        print(f"\n Safety net: caught {caught} of {len(summary['negatives'])} deliberately bad answers")
    print(f" Biggest risk: {summary['risk']}\n" + "=" * 100)


# ---- Email: HTML (inline CSS, tables only, no JavaScript) -------------------------------
def _e(text) -> str:
    return html.escape(str(text))


def _status(s: dict) -> str:
    if s["ok"]:
        return "✅ OK"
    return "➖ Weak metric (for information)" if s.get("informational") else "❌ Needs attention"


def _bar(score: float, ok: bool) -> str:
    """A score bar drawn with a table: one coloured cell sized in %, one grey cell for the rest."""
    pct = max(1, min(100, round(score * 100)))
    colour = "#2e7d32" if ok else "#c62828"
    return (f'<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse"><tr>'
            f'<td width="{pct}%" height="14" bgcolor="{colour}" style="background:{colour};font-size:1px;line-height:14px">&nbsp;</td>'
            f'<td width="{100 - pct}%" height="14" bgcolor="#e0e0e0" style="background:#e0e0e0;font-size:1px;line-height:14px">&nbsp;</td>'
            f'</tr></table>')


def _scorecard_html(summary: dict) -> str:
    rows = ""
    for s in summary["scorecard"]:
        sign = "&le;" if s["direction"] == "lower_is_better" else "&ge;"
        rows += (f'<tr><td style="padding:6px;border-bottom:1px solid #eee"><b>{_e(s["plain_name"])}</b>{" <i>(informational)</i>" if s.get("informational") else ""}<br>'
                 f'<span style="color:#666;font-size:12px">{_e(s["question_it_answers"])}</span></td>'
                 f'<td width="160" style="padding:6px;border-bottom:1px solid #eee">{_bar(s["avg"], s["ok"])}</td>'
                 f'<td style="padding:6px;border-bottom:1px solid #eee" align="right"><b>{s["avg"]:.2f}</b></td>'
                 f'<td style="padding:6px;border-bottom:1px solid #eee;color:#666" align="right">needs {sign} {s["threshold"]:.2f}</td>'
                 f'<td style="padding:6px;border-bottom:1px solid #eee">{_status(s)}</td></tr>')
    return rows


def _failures_html(summary: dict) -> str:
    if not summary["groups"]:
        return '<p style="color:#2e7d32">Nothing went wrong in this run. 🎉</p>'
    out = ""
    for risk, items in summary["groups"].items():
        out += (f'<p style="background:#fdecea;padding:8px;margin:14px 0 4px 0;border-left:4px solid #c62828">'
                f'<b>Risk: {_e(risk)}</b> ({len(items)} failed check{"s" if len(items) != 1 else ""})</p>')
        for f in items[:3]:  # three examples per risk keeps the email short
            out += (f'<table width="100%" cellpadding="4" cellspacing="0" style="font-size:13px;margin-bottom:8px;border-bottom:1px solid #eee">'
                    f'<tr><td width="130" valign="top" style="color:#666">Question asked</td><td>{_e(f["question"])}</td></tr>'
                    f'<tr><td valign="top" style="color:#666">The bot said</td><td>{_e(f["bot_said"])}</td></tr>'
                    f'<tr><td valign="top" style="color:#666">The policy says</td><td>{_e(f["policy_says"])}</td></tr>'
                    f'<tr><td valign="top" style="color:#666">Check that failed</td><td>{_e(f["check"])}: {_e(f["what_happened"])} It {_e(f["score_text"])}.</td></tr>'
                    f'<tr><td valign="top" style="color:#666">Suggested owner</td><td>{_e(f["owner"])}</td></tr></table>')
        if len(items) > 3:
            out += f'<p style="color:#666;font-size:12px">...and {len(items) - 3} more like this (see scores.xlsx).</p>'
    return out


def _safety_net_html(summary: dict) -> str:
    if not summary["negatives"]:
        return "<p>Safety-net tests were not part of this run.</p>"
    rows = ""
    for r in summary["negatives"]:
        verdict = "✅ Safety net caught it" if r["ok"] else "❌ MISSED - the metric did not notice"
        rows += (f'<tr><td style="padding:5px;border-bottom:1px solid #eee">{_e(r["note"])}</td>'
                 f'<td style="padding:5px;border-bottom:1px solid #eee">{_e(metric_cfg(r["metric"])["plain_name"])} ({r["score"]:.2f})</td>'
                 f'<td style="padding:5px;border-bottom:1px solid #eee">{verdict}</td></tr>')
    return f'<table width="100%" cellspacing="0" style="font-size:13px">{rows}</table>'


def write_email_html(summary: dict) -> None:
    m = summary["meta"]
    body = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>RAG quality report</title></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,Helvetica,sans-serif;color:#222">
<table width="100%" cellpadding="0" cellspacing="0" bgcolor="#f4f4f4"><tr><td align="center">
<table width="720" cellpadding="16" cellspacing="0" bgcolor="#ffffff" style="max-width:720px;background:#ffffff">
<tr><td>
<table width="100%" cellpadding="12" cellspacing="0"><tr>
<td width="110" align="center" bgcolor="{summary['colour']}" style="background:{summary['colour']};color:#ffffff;font-size:22px;font-weight:bold">{summary['light']}</td>
<td><span style="font-size:20px"><b>HR chatbot quality report</b></span><br>
<span style="color:#666;font-size:13px">{_e(m['date'])} &middot; bot mode: <b>{_e(m['bot_mode'])}</b> &middot; bot model: {_e(m['bot_llm'])} &middot; judge model: {_e(m['judge_llm'])}</span></td></tr></table>
<h3 style="margin-bottom:4px">Key numbers</h3>
<table width="100%" cellpadding="8" cellspacing="0" style="font-size:14px"><tr>
<td><b style="font-size:24px">{summary['n_questions']}</b><br>questions tested</td>
<td><b style="font-size:24px">{summary['pass_rate']:.0%}</b><br>of {summary['n_checks']} quality checks passed</td>
<td width="50%"><b>Biggest risk this run</b><br>{_e(summary['risk'])}</td></tr></table>
<h3 style="margin-bottom:4px">Scorecard</h3>
<table width="100%" cellspacing="0" style="font-size:13px">{_scorecard_html(summary)}</table>
<h3 style="margin-bottom:4px">What went wrong, in plain English</h3>{_failures_html(summary)}
<h3 style="margin-bottom:4px">What our safety net caught</h3>
<p style="font-size:13px;color:#666;margin-top:0">We feed the metrics deliberately bad answers. Each one should be flagged. If it is, the safety net works.</p>{_safety_net_html(summary)}
<h3 style="margin-bottom:4px">Appendix</h3>
<p style="font-size:12px;color:#666">Scores come from Ragas metrics judged by {_e(m['judge_llm'])}. Pass lines are set in config.yaml and tuned over time.
Full per-test details: <b>{HTML_REPORT_NAME}</b>; all scores: scores.xlsx; chart: metric_scores.png.</p>
</td></tr></table></td></tr></table></body></html>"""
    (REPORTS_DIR / "email_report.html").write_text(body, encoding="utf-8")


# ---- Email: Markdown (pastes into Teams, Slack, Confluence) -----------------------------
def write_email_md(summary: dict) -> None:
    m = summary["meta"]
    icon = {"GREEN": "🟢", "AMBER": "🟡", "RED": "🔴"}[summary["light"]]
    lines = [f"# {icon} HR chatbot quality report: {summary['light']}",
             f"{m['date']} | bot mode: **{m['bot_mode']}** | bot model: {m['bot_llm']} | judge model: {m['judge_llm']}", "",
             "## Key numbers",
             f"- Questions tested: **{summary['n_questions']}**",
             f"- Quality checks passed: **{summary['pass_rate']:.0%}** ({summary['n_checks']} checks)",
             f"- Biggest risk this run: {summary['risk']}", "",
             "## Scorecard", "| Check | Score | Pass line | Status |", "|---|---|---|---|"]
    for s in summary["scorecard"]:
        sign = "<=" if s["direction"] == "lower_is_better" else ">="
        lines.append(f"| {s['plain_name']}{' (informational)' if s.get('informational') else ''} | {s['avg']:.2f} | {sign} {s['threshold']:.2f} | {_status(s)} |")
    lines += ["", "## What went wrong, in plain English"]
    if not summary["groups"]:
        lines.append("Nothing went wrong in this run. 🎉")
    for risk, items in summary["groups"].items():
        lines += ["", f"### Risk: {risk} ({len(items)} failed)"]
        for f in items[:3]:
            lines += [f"- **Question:** {f['question']}", f"  - The bot said: {f['bot_said']}",
                      f"  - The policy says: {f['policy_says']}",
                      f"  - Failed check: {f['check']}: {f['what_happened']} It {f['score_text']}.",
                      f"  - Suggested owner: {f['owner']}"]
    lines += ["", "## What our safety net caught"]
    for r in summary["negatives"]:
        lines.append(f"- {r['note']} -> {metric_cfg(r['metric'])['plain_name']} ({r['score']:.2f}): "
                     f"{'✅ Safety net caught it' if r['ok'] else '❌ MISSED'}")
    lines += ["", "## Appendix",
              f"Scores come from Ragas metrics judged by {m['judge_llm']}. Details: `{HTML_REPORT_NAME}`, `scores.xlsx`, `metric_scores.png`."]
    (REPORTS_DIR / "email_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---- Entry point ------------------------------------------------------------------------
def build_all() -> None:
    rows = load_results()
    if not rows:
        print("No results found - nothing to report.")
        return
    REPORTS_DIR.mkdir(exist_ok=True)
    summary = build_summary(rows)
    write_csv_and_excel(rows)
    write_chart(summary)
    write_email_html(summary)
    write_email_md(summary)
    print_console_summary(summary)


if __name__ == "__main__":
    build_all()
