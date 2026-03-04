"""Punishment trigger interface for external devices/services."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from chess_punisher.observability import get_logger

LOGGER = get_logger(__name__)


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
        LOGGER.info(
            "punish_trigger",
            extra={
                "mover": event.mover,
                "severity": event.severity,
                "move_uci": event.move_uci,
                "loss_cp": event.loss_cp,
                "url": url or "",
            },
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
            LOGGER.warning("punish_request_failed", extra={"error": str(exc)})
