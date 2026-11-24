# 15-minute demo script

**Before the session (do once, 10 min ahead):** `python run_demo.py` and `python run_demo.py --buggy` so both runs are cached. Re-running is then instant and free, with identical numbers. Have open: terminal, `reports/` folder. Re-run the good one last so `reports/` shows it first (or copy the buggy reports aside).

## 0:00 - The problem (2 min)
**Say:** "Our HR chatbot answers from policy documents. It can fail in two ways: it can fetch the wrong pages, or it can say things that aren't in the documents. Nobody notices until an employee acts on a wrong answer. Today I'll show how we test that automatically."
**Show:** `data/knowledge_base/01_vacation_and_leave.md` ("15 vacation days"). "Anyone can check right from wrong here."

## 2:00 - The bot in 60 seconds (2 min)
**Show:** `chatbot/rag_bot.py`, scroll the numbered comments. **Say:** "Find the 3 best pages, send them to Claude Haiku, say 'answer only from these'. That's all RAG is."
**Show:** `data/golden_dataset.json`. "Ten questions with approved answers: simple lookups, answers spread over two documents, rephrased questions, and one that is NOT in our documents."

## 4:00 - Run the good bot (3 min)
**Run:** `python run_demo.py`
**While it runs, say:** "Each question is a separate pass/fail line, per metric. A second, stronger Claude (Sonnet) acts as the judge."
**Point at the console table:** "Plain-English names. 'Sticks to the facts', 'Finds the right pages'. Green ticks mean healthy." Mention the ➖ rows: "Word-matching metrics are free but weak for chat, so they're informational."
**Open** `reports/metric_scores.png`: "Bar = score, black tick = pass line."

## 7:00 - What each metric means (2 min)
**Open** `METRICS.md`. Use three analogies only: Faithfulness = open-book exam where you may only quote the book; Context Recall = packing for a trip with a checklist; Noise Sensitivity = repeating a random sentence from the wrong chapter (the only one where lower is better).

## 9:00 - Break it on purpose (3 min)
**Say:** "Now I'll make the bot worse: random page retrieval, and a prompt that allows guessing. This is what a bad deployment or a careless prompt change looks like."
**Run:** `python run_demo.py --buggy`
**Point at:** red lines in the console; the traffic light turning RED/AMBER.
**Open** `reports/email_report.html` in a browser. Walk top to bottom:
1. Traffic light + biggest risk ("The bot may invent policies...").
2. Scorecard bars.
3. **"What went wrong, in plain English"**: pick the stock-options question. "The bot was asked something not in our documents. It guessed. Policy says: we don't know. Why it matters: HR/legal exposure. Owner: Engineering, prompt and guardrails."
**Say:** "No test IDs. A manager can forward this as-is." Show `email_report.md` pastes into Teams.

## 12:00 - Who tests the tests? (2 min)
**Open** the "What our safety net caught" section (also `tests/negative/test_bad_bot_cases.py`). **Say:** "We feed each metric a deliberately bad answer: an invented policy, '30 days' instead of 15, off-topic text. The test passes when the metric raises the alarm. If one ever says MISSED, our alarm has gone blind."

## 14:00 - Wrap-up and Q&A (1 min)
**Say:** "It runs on every push in CI (`.github/workflows/ragas-tests.yml`), thresholds are in one YAML file, and the report is written for business readers." 
**Likely questions:** *Cost?* Repeat runs are cached. *Can we trust an LLM judge?* That's why the safety-net tests exist and thresholds get tuned over time. *Why not exact match?* See METRICS.md: one correct answer has many wordings.

## If something goes wrong live
No key: tests skip with a message (set `ANTHROPIC_API_KEY` in `.env`). Slow: you skipped the pre-run, use `--group generation` for a fast subset. Want to reset: `make clean-cache`.
