# chess-punisher

Minimal Python foundation for a future computer-vision + Stockfish project.

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

## Move Harness

Run:

```bash
make harness
```

The harness supports commands: `reset`, `log`, `clearlog`, `quit`.
