"""Punishment trigger interface for external devices/services."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class PunishEvent:
    mover: str
    severity: str
    move_uci: str
    loss_cp: int
    bestmove_uci: str


class Punisher:
    def __init__(
        self,
        white_url: str | None,
        black_url: str | None,
        dry_run: bool = False,
        timeout_s: float = 0.3,
    ) -> None:
        self.white_url = white_url or None
        self.black_url = black_url or None
        self.dry_run = dry_run
        self.timeout_s = timeout_s

    def url_for_mover(self, mover: str) -> str | None:
        if mover == "white":
            return self.white_url
        if mover == "black":
            return self.black_url
        return None

    def trigger(self, event: PunishEvent) -> None:
        url = self.url_for_mover(event.mover)
        print(
            "[PUNISH] mover={} severity={} move={} loss={} url={}".format(
                event.mover,
                event.severity,
                event.move_uci,
                event.loss_cp,
                url or "",
            )
        )

        if self.dry_run or not url:
            return

        query = urlencode(
            {
                "severity": event.severity,
                "loss": str(event.loss_cp),
                "move": event.move_uci,
            }
        )
        target = f"{url}?{query}"
        req = Request(target, method="GET")
        try:
            with urlopen(req, timeout=self.timeout_s):
                pass
        except Exception as exc:
            print(f"[PUNISH][WARN] request failed: {exc}")
