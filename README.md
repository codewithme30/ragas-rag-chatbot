# RAG Quality Testing Demo (pytest + Ragas)

A small, readable framework that tests a tiny HR chatbot ("Northwind Corp") the way you would test real software, using **pytest** and **Ragas**. Built for new QA hires and for live demos to non-technical managers.

## What is RAG? (3 sentences)
RAG (Retrieval-Augmented Generation) is a chatbot that first **looks up** the relevant pages in your own documents and then **writes an answer** from only those pages. It is used so the bot answers from company facts instead of guessing. Testing it means checking both halves: did it find the right pages, and did it answer correctly from them?

```
Question -> Retrieve -> Answer -> Ragas judge -> Reports
            (find 3     (Claude    (Claude Sonnet   (HTML email, Excel,
             best pages) Haiku)     scores it)       chart, pytest-html)
```

## Setup
Requires Python 3.11.

```bash
python3.11 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then put your ANTHROPIC_API_KEY in .env
```
First run downloads the small embeddings model (~90 MB) from HuggingFace. On locked-down networks that block HuggingFace's "Xet" downloader, set `HF_HUB_DISABLE_XET=1`.

## Run it
```bash
python run_demo.py                    # everything + all reports
python run_demo.py --buggy            # the deliberately broken bot (red results)
python run_demo.py --group generation # one group: retrieval | generation | answer_quality | non_llm | negative
python run_demo.py --no-cache         # ignore saved answers (costs money)
```
Plain pytest works too (reports are built at the end of every pytest run):
```bash
pytest -m generation
pytest tests/retrieval/test_context_recall.py
pytest -k vacation_days
```
`make test | retrieval | generation | answer-quality | non-llm | negative | buggy | report | clean-cache`
(`make report` rebuilds the reports from the last run without re-testing; `make clean-cache` clears both the bot cache and the Ragas judge cache.)

No API key? Tests that call Claude are **skipped with a friendly message**; the report still builds.

## How to read the reports (all in `reports/`)
| File | For whom | What to look at |
|---|---|---|
| `email_report.html` / `.md` | Managers | Traffic light, scorecard bars, "What went wrong" grouped by business risk, "What our safety net caught". Markdown pastes into Teams/Slack/Confluence. |
| `pytest_report.html` | QA | One row per question: score, pass line, bot answer, retrieved contexts. |
| `scores.xlsx` / `scores.csv` | Analysts | One row per question, one column per metric; green/red cells; Summary sheet. |
| `metric_scores.png` | Slides | Average per metric; black tick = pass line; red = failing. |
| Console table | Live demo | Plain-English summary printed after the run. |

Metrics marked *informational* (BLEU, ROUGE, String Similarity) are still tested but do not move the traffic light: they compare words, not meaning. See `METRICS.md`.

## Project layout
`chatbot/rag_bot.py` (the bot, read this first) · `tests/<group>/test_<metric>.py` (one file per metric) · `framework/` (config, judge, scoring, results, reports, business language) · `config.yaml` (models, thresholds, plain-English text) · `data/` (HR docs, golden questions, bad-bot cases).

## Rough cost and time per run (estimate, not measured)
~13 Haiku bot calls plus roughly 300 Sonnet judge calls for the full suite, so on the order of **US$0.50 to $1.50** and **5 to 10 minutes** on the first run. Repeat runs hit the disk caches (`.cache/`): effectively free and about a minute (mostly model loading). `--buggy` pays once for its own answers. Check your own bill after the first run and adjust this line.

## Notes for maintainers
- Ragas is pinned to **0.4.4**, which uses its new `ragas.metrics.collections` API (keyword inputs, no `SingleTurnSample`). Our `framework/scoring.py` hides that detail.
- `instructor` and `openai` are pinned explicitly: Ragas leaves them open and pip can pick versions that break Anthropic support.
- Thresholds in `config.yaml` are starting points. Teams tune them over time.
