"""Minimal in-memory command tracker for MQTT actuation."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from chess_punisher.observability import get_logger

from .protocol import CommandAck, PunishCommand

LOGGER = get_logger(__name__)


@dataclass
class PendingCommand:
    command: PunishCommand
    deadline_s: float
    attempts: int = 1
    acked: bool = False


class MqttCommandTracker:
    """Tracks command ACK state; transport implementation can be plugged later."""

    def __init__(self, ack_timeout_s: float = 0.6, max_attempts: int = 3) -> None:
        self.ack_timeout_s = ack_timeout_s
        self.max_attempts = max_attempts
        self._pending: dict[str, PendingCommand] = {}

    def register(self, command: PunishCommand) -> PendingCommand:
        now = monotonic()
        pending = PendingCommand(command=command, deadline_s=now + self.ack_timeout_s)
        self._pending[command.command_id] = pending
        LOGGER.info(
            "command_registered",
            extra={
                "command_id": command.command_id,
                "seq": command.seq,
                "deadline_s": pending.deadline_s,
            },
        )
        return pending

    def mark_ack(self, ack: CommandAck) -> bool:
        pending = self._pending.get(ack.command_id)
        if pending is None:
            LOGGER.warning("ack_unknown_command", extra={"command_id": ack.command_id})
            return False
        if ack.state == "executed":
            pending.acked = True
            del self._pending[ack.command_id]
            LOGGER.info("command_executed", extra={"command_id": ack.command_id})
            return True
        LOGGER.info("command_ack_state", extra={"command_id": ack.command_id, "state": ack.state})
        return False

    def due_retries(self) -> list[PunishCommand]:
        now = monotonic()
        retries: list[PunishCommand] = []
        for command_id, pending in list(self._pending.items()):
            if pending.acked:
                continue
            if now < pending.deadline_s:
                continue
            if pending.attempts >= self.max_attempts:
                LOGGER.error(
                    "command_retry_exhausted",
                    extra={"command_id": command_id, "attempts": pending.attempts},
                )
                del self._pending[command_id]
                continue
            pending.attempts += 1
            pending.deadline_s = now + self.ack_timeout_s
            LOGGER.warning(
                "command_retry_due",
                extra={"command_id": command_id, "attempts": pending.attempts},
            )
            retries.append(pending.command)
        return retries
