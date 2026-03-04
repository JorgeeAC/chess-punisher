import queue
import unittest
from pathlib import Path
import sys

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from chess_punisher.actuation.mqtt_adapter import MqttActuatorAdapter
from chess_punisher.actuation.mqtt_dispatcher import MqttCommandTracker
from chess_punisher.actuation.protocol import CommandAck, PunishCommand


class FakeTransport:
    def __init__(self) -> None:
        self.acks: queue.Queue[CommandAck] = queue.Queue()
        self.published: list[tuple[str, str, int]] = []

    def publish(self, topic: str, payload: str, qos: int = 1) -> None:
        self.published.append((topic, payload, qos))

    def recv_ack(self, timeout_s: float) -> CommandAck | None:
        try:
            return self.acks.get(timeout=timeout_s)
        except queue.Empty:
            return None

    def close(self) -> None:
        return


class MqttAdapterTests(unittest.TestCase):
    def test_send_and_wait_success(self) -> None:
        transport = FakeTransport()
        tracker = MqttCommandTracker(ack_timeout_s=0.05, max_attempts=2)
        adapter = MqttActuatorAdapter(device_id="esp32-1", tracker=tracker, transport=transport)

        command = PunishCommand(
            command_id="c1",
            game_id="g1",
            seq=1,
            action="tap",
            severity="MISTAKE",
            pulse_ms=100,
            ttl_ms=1000,
            created_at="2026-03-04T12:00:00Z",
        )
        transport.acks.put(CommandAck(command_id="c1", state="executed", ts_ms=123))
        ok = adapter.send_and_wait(command)
        self.assertTrue(ok)
        self.assertEqual(len(transport.published), 1)


if __name__ == "__main__":
    unittest.main()
