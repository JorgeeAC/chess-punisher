SHELL := /bin/bash
PY := python
PIP := pip

.PHONY: help venv install freeze smoke harness vision app probe-http light-test test fw-build fw-flash fw-monitor

help:
	@echo "Targets:"
	@echo "  make venv      - create .venv"
	@echo "  make install   - install project and dependencies"
	@echo "  make freeze    - write locked dependencies to requirements.txt"
	@echo "  make smoke     - run Stockfish smoke test"
	@echo "  make harness   - run interactive move harness"
	@echo "  make vision    - run live camera preview"
	@echo "  make app       - run app skeleton with state machine bootstrap"
	@echo "  make probe-http - send a basic HTTP confirmation call to the ESP32"
	@echo "  make light-test - send a longer visible LED pulse to the ESP32"
	@echo "  make test      - run unit tests"
	@echo "  make fw-build  - build ESP32 firmware (PlatformIO)"
	@echo "  make fw-flash  - flash ESP32 firmware (PORT=/dev/ttyUSB0)"
	@echo "  make fw-monitor - open ESP32 serial monitor (PORT=/dev/ttyUSB0)"

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

app:
	$(PY) -m chess_punisher.app.main

probe-http:
	$(PY) -m scripts.http_probe $${ESP_URL:+--url "$$ESP_URL"}

light-test:
	$(PY) -m scripts.http_probe \
		$${ESP_URL:+--url "$$ESP_URL"} \
		--skip-health \
		--severity LIGHT_TEST \
		--move led \
		--pulse-ms $${PULSE_MS:-2000}

test:
	$(PY) -m unittest discover -s tests -p "test_*.py"

fw-build:
	cd firmware/esp32_actuator && pio run -e esp32dev

fw-flash:
	cd firmware/esp32_actuator && pio run -e esp32dev -t upload --upload-port $${PORT:-/dev/ttyUSB0}

fw-monitor:
	cd firmware/esp32_actuator && pio device monitor --port $${PORT:-/dev/ttyUSB0} --baud 115200
