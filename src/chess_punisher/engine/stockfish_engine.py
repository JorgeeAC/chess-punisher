"""Minimal Stockfish wrapper using python-chess UCI support."""

from __future__ import annotations

import os
from pathlib import Path

import chess
import chess.engine


def _stockfish_path() -> Path:
    return Path(os.getenv("STOCKFISH_PATH", "./bin/stockfish"))


def _require_stockfish_binary() -> Path:
    path = _stockfish_path()
    if not path.exists():
        raise RuntimeError(
            f"Stockfish binary not found at '{path}'. "
            "Set STOCKFISH_PATH or place the binary at ./bin/stockfish."
        )
    return path


def _format_score(score: chess.engine.PovScore) -> str:
    """Render a UCI score as a compact human-readable string."""
    white_score = score.white()
    if white_score.is_mate():
        mate_in = white_score.mate()
        if mate_in is None:
            return "mate: unknown"
        side = "White" if mate_in > 0 else "Black"
        return f"mate in {abs(mate_in)} ({side})"

    cp = white_score.score()
    if cp is None:
        return "cp: unknown"
    return f"{cp / 100.0:+.2f} pawns (White)"


def analyse_board(board: chess.Board, time_limit_s: float = 0.1) -> chess.engine.PovScore:
    """Analyze a board and return the engine score object."""
    stockfish_path = _require_stockfish_binary()
    with chess.engine.SimpleEngine.popen_uci(str(stockfish_path)) as engine:
        info = engine.analyse(board, chess.engine.Limit(time=time_limit_s))

    score = info.get("score")
    if score is None:
        raise RuntimeError("Engine analysis did not return a score.")
    return score


def best_move(board: chess.Board, time_limit_s: float = 0.1) -> chess.Move:
    """Return the engine's best move for the current position."""
    stockfish_path = _require_stockfish_binary()
    with chess.engine.SimpleEngine.popen_uci(str(stockfish_path)) as engine:
        result = engine.play(board, chess.engine.Limit(time=time_limit_s))

    if result.move is None:
        raise RuntimeError("Engine did not return a move.")
    return result.move


def analyse_fen(fen: str, time_limit_s: float = 0.1) -> str:
    """Analyze a FEN with Stockfish and return a readable evaluation string."""
    board = chess.Board(fen)
    score = analyse_board(board, time_limit_s=time_limit_s)
    return _format_score(score)
