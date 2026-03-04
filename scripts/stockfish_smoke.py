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
from chess_punisher.observability import bind_correlation_id, configure_logging, get_logger

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
LOGGER = get_logger(__name__)


def main() -> int:
    configure_logging()
    with bind_correlation_id():
        try:
            evaluation = analyse_fen(STARTING_FEN, time_limit_s=0.1)
        except RuntimeError as exc:
            LOGGER.error("stockfish_smoke_failed", extra={"error": str(exc)})
            print(f"Smoke test failed: {exc}")
            return 1
        except ValueError as exc:
            LOGGER.error("stockfish_smoke_invalid_fen", extra={"error": str(exc)})
            print(f"Invalid FEN input: {exc}")
            return 1

        LOGGER.info("stockfish_smoke_passed", extra={"evaluation": evaluation})
        print(f"Smoke test passed. Starting position eval: {evaluation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
