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

# MQTT mode (ESP over broker)
python -m scripts.move_harness --actuation-mode mqtt --mqtt-host 127.0.0.1 --mqtt-port 1883 --mqtt-device-id esp32-1
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
