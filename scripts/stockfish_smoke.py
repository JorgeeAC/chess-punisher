"""Smoke test for Stockfish integration."""

from __future__ import annotations

from pathlib import Path
import sys

# Keep the script runnable without requiring editable install first.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from chess_punisher.engine.stockfish_engine import analyse_fen

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def main() -> int:
    try:
        evaluation = analyse_fen(STARTING_FEN, time_limit_s=0.1)
    except RuntimeError as exc:
        print(f"Smoke test failed: {exc}")
        return 1
    except ValueError as exc:
        print(f"Invalid FEN input: {exc}")
        return 1

    print(f"Smoke test passed. Starting position eval: {evaluation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
