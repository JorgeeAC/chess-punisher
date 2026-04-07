"""MQTT probe utility for Pi <-> ESP32 confirmation."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import queue
import secrets
from time import monotonic

from .protocol import ActuatorStatus, CommandAck, PunishCommand, ack_topic, command_topic, status_topic


@dataclass(frozen=True)
class ProbeResult:
    status_seen: bool
    received_seen: bool
    executed_seen: bool
    last_status: ActuatorStatus | None = None

    @property
    def ok(self) -> bool:
        return self.received_seen and self.executed_seen


def build_probe_command(device_id: str, pulse_ms: int = 150) -> PunishCommand:
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%d%H%M%S")
    suffix = secrets.token_hex(3)
    return PunishCommand(
        command_id=f"probe-{device_id}-{stamp}-{suffix}",
        game_id=f"probe-{stamp}",
        seq=1,
        action="tap",
        severity="INFO",
        pulse_ms=pulse_ms,
        ttl_ms=3000,
        created_at=now.isoformat(),
    )


class ProbeClient:
    def __init__(
        self,
        host: str,
        port: int,
        device_id: str,
        client_id: str,
    ) -> None:
        try:
            import paho.mqtt.client as mqtt  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "paho-mqtt is required for the probe. Install dependencies via make install."
            ) from exc

        self._device_id = device_id
        self._ack_topic = ack_topic(device_id)
        self._status_topic = status_topic(device_id)
        self._ack_queue: queue.Queue[CommandAck] = queue.Queue()
        self._status_queue: queue.Queue[ActuatorStatus] = queue.Queue()
        self._mqtt = mqtt.Client(client_id=client_id)
        self._mqtt.on_message = self._on_message
        self._mqtt.connect(host, port, keepalive=30)
        self._mqtt.subscribe(self._ack_topic, qos=1)
        self._mqtt.subscribe(self._status_topic, qos=1)
        self._mqtt.loop_start()

    def _on_message(self, _client: object, _userdata: object, msg: object) -> None:
        topic = msg.topic
        payload_raw = msg.payload.decode("utf-8")
        try:
            if topic == self._ack_topic:
                self._ack_queue.put_nowait(CommandAck.from_json(payload_raw))
            elif topic == self._status_topic:
                self._status_queue.put_nowait(ActuatorStatus.from_json(payload_raw))
        except Exception:
            return

    def publish_command(self, command: PunishCommand) -> None:
        self._mqtt.publish(command_topic(self._device_id), command.to_json(), qos=1)

    def recv_ack(self, timeout_s: float) -> CommandAck | None:
        try:
            return self._ack_queue.get(timeout=timeout_s)
        except queue.Empty:
            return None

    def recv_status(self, timeout_s: float) -> ActuatorStatus | None:
        try:
            return self._status_queue.get(timeout=timeout_s)
        except queue.Empty:
            return None

    def close(self) -> None:
        self._mqtt.loop_stop()
        self._mqtt.disconnect()


def run_probe(
    host: str,
    port: int,
    device_id: str,
    client_id: str,
    pulse_ms: int,
    timeout_s: float,
    listen_only: bool = False,
) -> ProbeResult:
    client = ProbeClient(host=host, port=port, device_id=device_id, client_id=client_id)
    try:
        print(f"Listening for {device_id} on MQTT {host}:{port}")
        status = client.recv_status(timeout_s=1.5)
        if status is not None:
            print(
                "status:",
                f"online={status.online}",
                f"firmware={status.firmware}",
                f"last_command_id={status.last_command_id}",
                f"rssi={status.rssi}",
            )

        if listen_only:
            return ProbeResult(
                status_seen=status is not None,
                received_seen=False,
                executed_seen=False,
                last_status=status,
            )

        command = build_probe_command(device_id=device_id, pulse_ms=pulse_ms)
        print(f"sending probe command {command.command_id} to {command_topic(device_id)}")
        client.publish_command(command)

        received_seen = False
        executed_seen = False
        last_status = status
        deadline = monotonic() + timeout_s
        while monotonic() < deadline and not executed_seen:
            ack = client.recv_ack(timeout_s=0.1)
            if ack is not None and ack.command_id == command.command_id:
                print(f"ack: state={ack.state} ts_ms={ack.ts_ms}")
                if ack.state == "received":
                    received_seen = True
                if ack.state == "executed":
                    executed_seen = True

            maybe_status = client.recv_status(timeout_s=0.01)
            if maybe_status is not None:
                last_status = maybe_status
                print(
                    "status:",
                    f"online={maybe_status.online}",
                    f"firmware={maybe_status.firmware}",
                    f"last_command_id={maybe_status.last_command_id}",
                    f"rssi={maybe_status.rssi}",
                )

        return ProbeResult(
            status_seen=last_status is not None,
            received_seen=received_seen,
            executed_seen=executed_seen,
            last_status=last_status,
        )
    finally:
        client.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Basic MQTT probe for ESP32 actuator.")
    parser.add_argument("--mqtt-host", default="127.0.0.1", help="MQTT broker host.")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port.")
    parser.add_argument("--mqtt-device-id", default="esp32-1", help="ESP32 device id.")
    parser.add_argument(
        "--mqtt-client-id",
        default="chess-punisher-probe",
        help="MQTT client id for the probe.",
    )
    parser.add_argument(
        "--pulse-ms",
        type=int,
        default=150,
        help="Indicator pulse width for the confirmation command.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="How long to wait for the executed ACK.",
    )
    parser.add_argument(
        "--listen-only",
        action="store_true",
        help="Only listen for retained status without sending a command.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = run_probe(
            host=args.mqtt_host,
            port=args.mqtt_port,
            device_id=args.mqtt_device_id,
            client_id=args.mqtt_client_id,
            pulse_ms=args.pulse_ms,
            timeout_s=args.timeout,
            listen_only=args.listen_only,
        )
    except RuntimeError as exc:
        print(f"Probe error: {exc}")
        return 1
    except OSError as exc:
        print(f"Probe connection error: {exc}")
        return 1

    if args.listen_only:
        if result.status_seen:
            print("Probe success: ESP32 status is visible on MQTT.")
            return 0
        print("Probe timeout: no retained status seen from the ESP32.")
        return 1

    if result.ok:
        print("Probe success: Pi -> broker -> ESP32 -> ACK path is working.")
        return 0

    print(
        "Probe timeout:",
        f"status_seen={result.status_seen}",
        f"received_seen={result.received_seen}",
        f"executed_seen={result.executed_seen}",
    )
    return 1
