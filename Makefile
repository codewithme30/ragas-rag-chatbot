# Shortcuts. On Windows without make, use: python run_demo.py [--buggy] [--group <name>]
PY ?= python

install:
	$(PY) -m venv .venv
	.venv/bin/pip install -r requirements.txt
	@echo "Now: cp .env.example .env  and add your ANTHROPIC_API_KEY. Use .venv/bin/python (or activate .venv) afterwards."

test:
	$(PY) run_demo.py

retrieval:
	$(PY) run_demo.py --group retrieval

generation:
	$(PY) run_demo.py --group generation

answer-quality:
	$(PY) run_demo.py --group answer_quality

non-llm:
	$(PY) run_demo.py --group non_llm

negative:
	$(PY) run_demo.py --group negative

buggy:
	$(PY) run_demo.py --buggy

report:  # rebuild all reports from the last run's scores, without re-testing
	$(PY) -m framework.reports

clean-cache:  # forget saved bot answers AND judge answers (the next run costs money again)
	$(PY) -c "import shutil; shutil.rmtree('.cache', ignore_errors=True); print('cache cleared')"

.PHONY: install test retrieval generation answer-quality non-llm negative buggy report clean-cache
