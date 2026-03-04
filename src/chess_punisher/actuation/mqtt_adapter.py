"""Thin MQTT adapter for actuator commands with ACK/retry handling."""

from __future__ import annotations

from dataclasses import dataclass
import queue
from time import monotonic
from typing import Protocol

from chess_punisher.observability import get_logger

from .mqtt_dispatcher import MqttCommandTracker
from .protocol import CommandAck, PunishCommand, ack_topic, command_topic

LOGGER = get_logger(__name__)


class AckTransport(Protocol):
    def publish(self, topic: str, payload: str, qos: int = 1) -> None: ...

    def recv_ack(self, timeout_s: float) -> CommandAck | None: ...

    def close(self) -> None: ...


class PahoAckTransport:
    """Real MQTT transport based on paho-mqtt."""

    def __init__(
        self,
        host: str,
        port: int,
        device_id: str,
        client_id: str = "chess-punisher-pi",
    ) -> None:
        try:
            import paho.mqtt.client as mqtt  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "paho-mqtt is required for MQTT mode. Install dependencies via make install."
            ) from exc

        self._ack_topic = ack_topic(device_id)
        self._ack_queue: queue.Queue[CommandAck] = queue.Queue()
        self._mqtt = mqtt.Client(client_id=client_id)
        self._mqtt.on_message = self._on_message
        self._mqtt.connect(host, port, keepalive=30)
        self._mqtt.subscribe(self._ack_topic, qos=1)
        self._mqtt.loop_start()
        LOGGER.info(
            "mqtt_transport_connected",
            extra={"host": host, "port": port, "ack_topic": self._ack_topic},
        )

    def _on_message(self, _client: object, _userdata: object, msg: object) -> None:
        try:
            payload_raw = msg.payload.decode("utf-8")
            ack = CommandAck.from_json(payload_raw)
            self._ack_queue.put_nowait(ack)
        except Exception:
            LOGGER.warning("mqtt_ack_parse_failed", exc_info=True)

    def publish(self, topic: str, payload: str, qos: int = 1) -> None:
        self._mqtt.publish(topic, payload, qos=qos)

    def recv_ack(self, timeout_s: float) -> CommandAck | None:
        try:
            return self._ack_queue.get(timeout=timeout_s)
        except queue.Empty:
            return None

    def close(self) -> None:
        self._mqtt.loop_stop()
        self._mqtt.disconnect()


@dataclass
class MqttActuatorAdapter:
    device_id: str
    tracker: MqttCommandTracker
    transport: AckTransport

    def send_and_wait(self, command: PunishCommand) -> bool:
        topic = command_topic(self.device_id)
        self.tracker.register(command)
        self.transport.publish(topic, command.to_json(), qos=1)
        LOGGER.info(
            "mqtt_command_sent",
            extra={
                "device_id": self.device_id,
                "command_id": command.command_id,
                "topic": topic,
            },
        )

        deadline = monotonic() + (self.tracker.ack_timeout_s * self.tracker.max_attempts) + 0.2
        while monotonic() < deadline:
            ack = self.transport.recv_ack(timeout_s=0.05)
            if ack is not None:
                is_executed = self.tracker.mark_ack(ack)
                if ack.command_id == command.command_id and is_executed:
                    return True

            for retry_command in self.tracker.due_retries():
                self.transport.publish(topic, retry_command.to_json(), qos=1)

        LOGGER.error(
            "mqtt_command_timeout",
            extra={"command_id": command.command_id, "device_id": self.device_id},
        )
        return False

    def close(self) -> None:
        self.transport.close()
