"""Current game move logging utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MoveLogEntry:
    move_uci: str
    mover: str
    bestmove_uci: str
    eval_before_cp: int
    eval_after_cp: int
    loss_cp: int
    classification: str


def format_entry(entry: MoveLogEntry) -> str:
    return (
        "move={} mover={} bestmove={} eval_before={} eval_after={} loss={} class={}".format(
            entry.move_uci,
            entry.mover,
            entry.bestmove_uci,
            entry.eval_before_cp,
            entry.eval_after_cp,
            entry.loss_cp,
            entry.classification,
        )
    )


class GameLogger:
    def __init__(self, log_path: str | None = None) -> None:
        self.log_path = Path(log_path) if log_path else None
        self._entries: list[MoveLogEntry] = []

    def log_move(self, entry: MoveLogEntry) -> None:
        self._entries.append(entry)
        if self.log_path is None:
            return

        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(format_entry(entry) + "\n")
        except OSError as exc:
            print(f"[LOG][WARN] unable to write {self.log_path}: {exc}")

    def reset(self) -> None:
        self._entries.clear()

    def tail(self, n: int = 10) -> list[MoveLogEntry]:
        if n <= 0:
            return []
        return self._entries[-n:]
