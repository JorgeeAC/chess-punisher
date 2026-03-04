import unittest
from pathlib import Path
import sys

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from chess_punisher.actuation.mqtt_dispatcher import MqttCommandTracker
from chess_punisher.actuation.protocol import CommandAck, PunishCommand


class MqttDispatcherTests(unittest.TestCase):
    def test_register_and_ack(self) -> None:
        tracker = MqttCommandTracker(ack_timeout_s=0.01, max_attempts=2)
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
        tracker.register(command)
        ok = tracker.mark_ack(CommandAck(command_id="c1", state="executed", ts_ms=42))
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
