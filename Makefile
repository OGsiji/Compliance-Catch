# Compliance Catch — thin convenience wrapper around the commands in
# REPRODUCTION.md. This Makefile only invokes existing entry points; it changes
# no logic in baseline/, agent/, or eval/. Windows users without `make` can run
# the raw python commands documented under each target in REPRODUCTION.md.

# Use the project venv's python if it exists, else the system python3.
PYTHON := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)

.PHONY: help setup baseline agent call eval test clean

# Override on the command line: make call CALL=call_09 PROVIDER=gemini
CALL ?= call_10
PROVIDER ?= gemini

help:  ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  %-10s %s\n", $$1, $$2}'

setup:  ## create the virtualenv and install dependencies
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

baseline:  ## run the two baselines over the fixtures (no API key needed)
	$(PYTHON) -c "from core.data import load_all_transcripts as L; from baseline.keyword_match import keyword_flags as K; print('keyword baseline — flags per call:'); [print(' ', t.id, sorted({f['policy_id'] for f in K(t)})) for t in L()]"
	$(PYTHON) -c "from core.data import load_all_transcripts as L; from baseline.random_sample import review as R; print('random 5% sample — reviewed:', {k: v['reviewed'] for k, v in R(L()).items()})"

agent:  ## run the Gemini agent over all transcripts (needs GEMINI_API_KEY)
	set -a; [ -f .env ] && . ./.env; set +a; $(PYTHON) -m agent.pipeline --provider gemini

call:  ## run one call: make call CALL=call_09 [PROVIDER=gemini|offline]
	set -a; [ -f .env ] && . ./.env; set +a; $(PYTHON) -m agent.pipeline --call $(CALL) --provider $(PROVIDER)

eval:  ## score baselines + Gemini agent vs ground truth (needs GEMINI_API_KEY)
	set -a; [ -f .env ] && . ./.env; set +a; $(PYTHON) -m eval.run_eval --provider gemini

test:  ## run the test suite (no API key needed)
	$(PYTHON) -m unittest discover -s tests -v

clean:  ## remove python caches and the virtualenv
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .venv
