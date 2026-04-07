# chess-punisher

Minimal Python foundation for a future computer-vision + Stockfish project.

The repo now includes initial scaffolding for:

- structured observability logs (JSON + correlation IDs)
- a lightweight orchestration state machine
- actuator protocol message schemas
- an ESP32 PlatformIO firmware skeleton

## Requirements

- Python 3.10+
- `direnv` installed
- Stockfish binary (not committed to this repository)

## Setup

1. Create and activate a virtual environment:
   ```bash
   make venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   make install
   ```
3. Allow `direnv` in this directory:
   ```bash
   direnv allow
   ```
4. Ensure `STOCKFISH_PATH` points to a valid binary:
   ```bash
   export STOCKFISH_PATH=/absolute/path/to/stockfish
   ```

`.envrc` auto-activates `.venv` (if present) and sets `STOCKFISH_PATH` for your local environment.

Optional punishment/logging env vars:

```bash
export PUNISHER_WHITE_URL="http://bracelet-white.local/punish"
export PUNISHER_BLACK_URL="http://bracelet-black.local/punish"
export PUNISHER_DRY_RUN="1"
export GAME_LOG_PATH="./.local/game.log"
```

## Smoke Test

Run:

```bash
make smoke
```

This executes `python -m scripts.stockfish_smoke`, runs a quick UCI analysis on the starting position, and prints an evaluation string.

## App Skeleton

Run:

```bash
make app
```

This boots the minimal orchestrator state machine and emits structured startup logs.

## Move Harness

Run:

```bash
make harness
```

The harness supports commands: `reset`, `log`, `clearlog`, `quit`.

Actuation modes:

```bash
# Existing HTTP punisher behavior (default)
make harness

# Simulator mode (no hardware)
python -m scripts.move_harness --actuation-mode sim
```

## Vision Preview (Raspberry Pi)

Install camera dependencies on Raspberry Pi:

```bash
sudo apt install -y python3-opencv python3-numpy python3-picamera2
```

Run the preview:

```bash
make vision
```

Optional overrides:

```bash
STREAM_BACKEND=auto VISION_GRAY=0 VISION_W=640 VISION_H=480 VISION_FPS=20 make vision
```

If you are connected over SSH and want the window on the Pi monitor:

```bash
export DISPLAY=:0
make vision
```

## Firmware (ESP32)

The firmware scaffold lives in `firmware/esp32_actuator`.

Build:

```bash
make fw-build
```

Flash (override serial port with `PORT` if needed):

```bash
PORT=/dev/ttyUSB0 make fw-flash
```

Open the serial monitor:

```bash
PORT=/dev/ttyUSB0 make fw-monitor
```

## Basic ESP32 <-> Raspberry Pi Confirmation

The lowest-friction path in this repo is now plain HTTP:

1. Put the ESP32 on Wi-Fi by setting `WIFI_SSID` and `WIFI_PASS` in `firmware/esp32_actuator/platformio.ini`, then flash it from your PC.
2. Keep the ESP32 plugged into USB and open the serial monitor:
   ```bash
   PORT=/dev/ttyUSB0 make fw-monitor
   ```
3. Read the ESP32 IP from serial output. The firmware serves `GET /health` and `GET /punish`.
4. From the Raspberry Pi, hit the ESP32 directly:
   ```bash
   curl "http://<esp-ip>/health"
   curl "http://<esp-ip>/punish?severity=TEST&loss=0&move=e2e4&pulse_ms=150"
   ```
5. Or use the repo helper:
   ```bash
   PUNISHER_WHITE_URL="http://<esp-ip>/punish" make probe-http
   ```

What success looks like:

- The Pi gets a JSON response from `/health` and `/punish`.
- The ESP32 serial monitor logs the request details.
- The ESP32 briefly flashes its indicator LED on `/punish`.

If your `.envrc` already exports `PUNISHER_WHITE_URL`, you can just run:

```bash
direnv allow
make probe-http
```
