"""Simple move quality classification based on evaluation loss."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

import chess
import chess.engine

MATE_CP_EQUIVALENT = 10_000
ScoreLike = Union[int, chess.engine.Score]


@dataclass(frozen=True)
class Thresholds:
    inaccuracy: int = 50
    mistake: int = 150
    blunder: int = 300


def _score_to_cp(score: ScoreLike) -> int:
    if isinstance(score, int):
        return score
    return score.score(mate_score=MATE_CP_EQUIVALENT)


def cp_loss(before_score: ScoreLike, after_score: ScoreLike) -> int:
    """Return centipawn loss, clamped at zero."""
    before_cp = _score_to_cp(before_score)
    after_cp = _score_to_cp(after_score)
    return max(0, before_cp - after_cp)


def classify_cp_loss(cp_loss: int, thresholds: Thresholds = Thresholds()) -> str:
    if cp_loss >= thresholds.blunder:
        return "BLUNDER"
    if cp_loss >= thresholds.mistake:
        return "MISTAKE"
    if cp_loss >= thresholds.inaccuracy:
        return "INACCURACY"
    return "OK"


def compute_cp_loss_for_mover(
    board_before: chess.Board,
    move: chess.Move,
    engine: chess.engine.SimpleEngine,
    time_limit_s: float,
) -> tuple[int, str]:
    """Compute centipawn loss and label from the mover's perspective."""
    if move not in board_before.legal_moves:
        raise ValueError(f"Illegal move for position: {move.uci()}")

    mover_color = board_before.turn
    limit = chess.engine.Limit(time=time_limit_s)

    info_before = engine.analyse(board_before, limit)
    raw_before = info_before.get("score")
    if raw_before is None:
        raise RuntimeError("Engine analysis did not return a score for pre-move position.")
    score_before = raw_before.pov(mover_color)
    before_cp = _score_to_cp(score_before)

    board_after = board_before.copy(stack=False)
    board_after.push(move)
    info_after = engine.analyse(board_after, limit)
    raw_after = info_after.get("score")
    if raw_after is None:
        raise RuntimeError("Engine analysis did not return a score for post-move position.")
    score_after = raw_after.pov(mover_color)
    after_cp = _score_to_cp(score_after)

    loss = max(0, before_cp - after_cp)
    return loss, classify_cp_loss(loss)
