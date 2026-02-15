SHELL := /bin/bash
PY := python
PIP := pip

.PHONY: help venv install freeze smoke harness vision test

help:
	@echo "Targets:"
	@echo "  make venv      - create .venv"
	@echo "  make install   - install project and dependencies"
	@echo "  make freeze    - write locked dependencies to requirements.txt"
	@echo "  make smoke     - run Stockfish smoke test"
	@echo "  make harness   - run interactive move harness"
	@echo "  make vision    - run live camera preview"
	@echo "  make test      - run unit tests"

venv:
	$(PY) -m venv .venv

install:
	$(PIP) install -r requirements.txt
	$(PIP) install -e .

freeze:
	$(PIP) freeze > requirements.txt

smoke:
	$(PY) -m scripts.stockfish_smoke

harness:
	$(PY) -m scripts.move_harness

vision:
	$(PY) -m scripts.vision_preview --backend $${STREAM_BACKEND:-auto} --gray $${VISION_GRAY:-0} --width $${VISION_W:-640} --height $${VISION_H:-480} --fps $${VISION_FPS:-20}

test:
	$(PY) -m unittest discover -s tests -p "test_*.py"
