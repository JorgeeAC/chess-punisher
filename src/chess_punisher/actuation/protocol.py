"""Message schemas for Pi <-> ESP actuator protocol."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

COMMAND_TOPIC_TEMPLATE = "cp/actuators/{device_id}/cmd"
ACK_TOPIC_TEMPLATE = "cp/actuators/{device_id}/ack"
STATUS_TOPIC_TEMPLATE = "cp/actuators/{device_id}/status"

ACK_STATES = {"received", "executed", "rejected"}
COMMAND_ACTIONS = {"tap", "press", "double_tap"}


def command_topic(device_id: str) -> str:
    return COMMAND_TOPIC_TEMPLATE.format(device_id=device_id)


def ack_topic(device_id: str) -> str:
    return ACK_TOPIC_TEMPLATE.format(device_id=device_id)


def status_topic(device_id: str) -> str:
    return STATUS_TOPIC_TEMPLATE.format(device_id=device_id)


@dataclass(frozen=True)
class PunishCommand:
    command_id: str
    game_id: str
    seq: int
    action: str
    severity: str
    pulse_ms: int
    ttl_ms: int
    created_at: str

    def validate(self) -> None:
        if not self.command_id:
            raise ValueError("command_id is required")
        if not self.game_id:
            raise ValueError("game_id is required")
        if self.seq < 0:
            raise ValueError("seq must be >= 0")
        if self.action not in COMMAND_ACTIONS:
            raise ValueError(f"action must be one of: {sorted(COMMAND_ACTIONS)}")
        if self.pulse_ms <= 0:
            raise ValueError("pulse_ms must be > 0")
        if self.ttl_ms <= 0:
            raise ValueError("ttl_ms must be > 0")
        if not self.created_at:
            raise ValueError("created_at is required")

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "command_id": self.command_id,
            "game_id": self.game_id,
            "seq": self.seq,
            "action": self.action,
            "severity": self.severity,
            "pulse_ms": self.pulse_ms,
            "ttl_ms": self.ttl_ms,
            "created_at": self.created_at,
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), separators=(",", ":"))

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PunishCommand":
        cmd = cls(
            command_id=str(payload["command_id"]),
            game_id=str(payload["game_id"]),
            seq=int(payload["seq"]),
            action=str(payload["action"]),
            severity=str(payload["severity"]),
            pulse_ms=int(payload["pulse_ms"]),
            ttl_ms=int(payload["ttl_ms"]),
            created_at=str(payload["created_at"]),
        )
        cmd.validate()
        return cmd

    @classmethod
    def from_json(cls, raw: str) -> "PunishCommand":
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("command payload must be a JSON object")
        return cls.from_dict(payload)


@dataclass(frozen=True)
class CommandAck:
    command_id: str
    state: str
    ts_ms: int
    error: str = ""

    def validate(self) -> None:
        if not self.command_id:
            raise ValueError("command_id is required")
        if self.state not in ACK_STATES:
            raise ValueError(f"state must be one of: {sorted(ACK_STATES)}")
        if self.ts_ms <= 0:
            raise ValueError("ts_ms must be > 0")

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        payload = {"command_id": self.command_id, "state": self.state, "ts_ms": self.ts_ms}
        if self.error:
            payload["error"] = self.error
        return payload

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), separators=(",", ":"))

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CommandAck":
        ack = cls(
            command_id=str(payload["command_id"]),
            state=str(payload["state"]),
            ts_ms=int(payload["ts_ms"]),
            error=str(payload.get("error", "")),
        )
        ack.validate()
        return ack

    @classmethod
    def from_json(cls, raw: str) -> "CommandAck":
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("ack payload must be a JSON object")
        return cls.from_dict(payload)


@dataclass(frozen=True)
class ActuatorStatus:
    online: bool
    firmware: str
    last_command_id: str
    rssi: int | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "online": self.online,
            "firmware": self.firmware,
            "last_command_id": self.last_command_id,
        }
        if self.rssi is not None:
            payload["rssi"] = self.rssi
        return payload

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), separators=(",", ":"))

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ActuatorStatus":
        return cls(
            online=bool(payload["online"]),
            firmware=str(payload["firmware"]),
            last_command_id=str(payload["last_command_id"]),
            rssi=int(payload["rssi"]) if payload.get("rssi") is not None else None,
        )

    @classmethod
    def from_json(cls, raw: str) -> "ActuatorStatus":
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("status payload must be a JSON object")
        return cls.from_dict(payload)
