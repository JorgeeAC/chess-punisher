"""Simple actuator simulator for protocol testing."""

from __future__ import annotations

import time

from chess_punisher.actuation.protocol import CommandAck, PunishCommand


class EspActuatorSim:
    def __init__(self, execute_delay_ms: int = 120) -> None:
        self.execute_delay_ms = execute_delay_ms
        self.last_command_id: str = ""

    def execute(self, command: PunishCommand) -> list[CommandAck]:
        now_ms = int(time.time() * 1000)
        self.last_command_id = command.command_id
        return [
            CommandAck(command_id=command.command_id, state="received", ts_ms=now_ms),
            CommandAck(
                command_id=command.command_id,
                state="executed",
                ts_ms=now_ms + self.execute_delay_ms,
            ),
        ]
