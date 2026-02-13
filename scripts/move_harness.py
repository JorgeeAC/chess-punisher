"""Interactive move harness for blunder classification."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

import chess
import chess.engine

# Keep the script runnable without requiring editable install first.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from chess_punisher.engine.blunder_classifier import (
    MATE_CP_EQUIVALENT,
    Thresholds,
    classify_cp_loss,
    compute_cp_loss_for_mover,
)
from chess_punisher.comms.punisher import PunishEvent, Punisher
from chess_punisher.logging.game_logger import GameLogger, MoveLogEntry, format_entry


def _stockfish_path() -> Path:
    return Path(os.getenv("STOCKFISH_PATH", "./bin/stockfish"))


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _evaluate_cp_for_color(
    board: chess.Board,
    color: chess.Color,
    engine: chess.engine.SimpleEngine,
    time_limit_s: float,
) -> int:
    info = engine.analyse(board, chess.engine.Limit(time=time_limit_s))
    raw_score = info.get("score")
    if raw_score is None:
        raise RuntimeError("Engine analysis did not return a score.")
    score = raw_score.pov(color)
    return score.score(mate_score=MATE_CP_EQUIVALENT)


def _parse_thresholds(raw: str) -> Thresholds:
    try:
        inaccuracy, mistake, blunder = [int(x.strip()) for x in raw.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "thresholds must be three comma-separated integers like 50,150,300"
        ) from exc
    return Thresholds(inaccuracy=inaccuracy, mistake=mistake, blunder=blunder)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Interactive move classification harness.")
    parser.add_argument("--time", type=float, default=0.1, help="Engine think time in seconds.")
    parser.add_argument(
        "--thresholds",
        type=_parse_thresholds,
        default=Thresholds(),
        help="Centipawn thresholds inaccuracy,mistake,blunder (default: 50,150,300).",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    board = chess.Board()
    thresholds: Thresholds = args.thresholds
    time_limit_s: float = args.time
    default_thresholds = Thresholds()
    stockfish_path = _stockfish_path()
    punisher = Punisher(
        white_url=os.getenv("PUNISHER_WHITE_URL"),
        black_url=os.getenv("PUNISHER_BLACK_URL"),
        dry_run=_env_bool("PUNISHER_DRY_RUN", default=False),
        timeout_s=0.3,
    )
    logger = GameLogger(log_path=os.getenv("GAME_LOG_PATH"))

    if not stockfish_path.exists():
        print(
            f"Engine error: Stockfish binary not found at '{stockfish_path}'. "
            "Set STOCKFISH_PATH or place the binary at ./bin/stockfish."
        )
        return 1

    print("Enter UCI moves (e.g. e2e4). Commands: reset, log, clearlog, quit")
    try:
        with chess.engine.SimpleEngine.popen_uci(str(stockfish_path)) as engine:
            while True:
                raw = input("> ").strip().lower()
                if raw == "quit":
                    return 0
                if raw == "reset":
                    board.reset()
                    logger.reset()
                    print("Board reset.")
                    continue
                if raw == "log":
                    for entry in logger.tail(10):
                        print(format_entry(entry))
                    continue
                if raw == "clearlog":
                    logger.reset()
                    print("Log cleared.")
                    continue
                if not raw:
                    continue

                try:
                    move = chess.Move.from_uci(raw)
                except ValueError:
                    print(f"Invalid UCI move: {raw}")
                    continue
                if move not in board.legal_moves:
                    print(f"Illegal move: {raw}")
                    continue

                mover_color = board.turn
                mover_name = "white" if mover_color == chess.WHITE else "black"

                try:
                    eval_before = _evaluate_cp_for_color(
                        board, mover_color, engine, time_limit_s
                    )
                    suggested = engine.play(
                        board, chess.engine.Limit(time=time_limit_s)
                    ).move
                    if suggested is None:
                        raise RuntimeError("Engine did not return a move.")
                except RuntimeError as exc:
                    print(f"Engine error: {exc}")
                    return 1

                # Compute mover-aware loss/classification through shared classifier utility.
                try:
                    loss, label = compute_cp_loss_for_mover(
                        board_before=board,
                        move=move,
                        engine=engine,
                        time_limit_s=time_limit_s,
                    )
                except ValueError as exc:
                    print(f"Illegal move: {exc}")
                    continue
                except RuntimeError as exc:
                    print(f"Engine error: {exc}")
                    return 1

                if thresholds != default_thresholds:
                    label = classify_cp_loss(loss, thresholds=thresholds)

                board_after = board.copy(stack=False)
                board_after.push(move)
                eval_after = _evaluate_cp_for_color(
                    board_after, mover_color, engine, time_limit_s
                )

                entry = MoveLogEntry(
                    move_uci=move.uci(),
                    mover=mover_name,
                    bestmove_uci=suggested.uci(),
                    eval_before_cp=eval_before,
                    eval_after_cp=eval_after,
                    loss_cp=loss,
                    classification=label,
                )
                logger.log_move(entry)
                board.push(move)

                print(format_entry(entry))

                if label != "OK":
                    punisher.trigger(
                        PunishEvent(
                            mover=mover_name,
                            severity=label,
                            move_uci=move.uci(),
                            loss_cp=loss,
                            bestmove_uci=suggested.uci(),
                        )
                    )
    except OSError as exc:
        print(f"Engine error: failed to start Stockfish at '{stockfish_path}': {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
