"""Main app skeleton for future Pi runtime."""

from __future__ import annotations

from chess_punisher.observability import bind_correlation_id, configure_logging, get_logger
from chess_punisher.orchestrator import AppStateMachine, event

LOGGER = get_logger(__name__)


def run_once() -> None:
    machine = AppStateMachine()
    machine.handle(event("START"))
    machine.handle(event("CALIBRATION_STABLE", confidence=0.95))
    LOGGER.info("app_bootstrap_complete", extra={"state": machine.state.value})


def main() -> int:
    configure_logging()
    with bind_correlation_id():
        run_once()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
