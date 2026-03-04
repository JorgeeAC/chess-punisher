import json
import unittest

from pathlib import Path
import sys

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from chess_punisher.actuation.protocol import (
    CommandAck,
    PunishCommand,
    ack_topic,
    command_topic,
    status_topic,
)


class ProtocolTests(unittest.TestCase):
    def test_topic_helpers(self) -> None:
        self.assertEqual(command_topic("esp-a"), "cp/actuators/esp-a/cmd")
        self.assertEqual(ack_topic("esp-a"), "cp/actuators/esp-a/ack")
        self.assertEqual(status_topic("esp-a"), "cp/actuators/esp-a/status")

    def test_command_round_trip(self) -> None:
        command = PunishCommand(
            command_id="c1",
            game_id="g1",
            seq=12,
            action="tap",
            severity="BLUNDER",
            pulse_ms=180,
            ttl_ms=3000,
            created_at="2026-03-04T12:00:00Z",
        )
        raw = command.to_json()
        decoded = PunishCommand.from_json(raw)
        self.assertEqual(decoded.command_id, "c1")
        self.assertEqual(decoded.action, "tap")

    def test_command_validation(self) -> None:
        with self.assertRaises(ValueError):
            PunishCommand(
                command_id="",
                game_id="g1",
                seq=0,
                action="tap",
                severity="MISTAKE",
                pulse_ms=10,
                ttl_ms=1000,
                created_at="2026-03-04T12:00:00Z",
            ).validate()

    def test_ack_round_trip(self) -> None:
        ack = CommandAck(command_id="c1", state="executed", ts_ms=1234)
        payload = json.loads(ack.to_json())
        self.assertEqual(payload["state"], "executed")
        decoded = CommandAck.from_dict(payload)
        self.assertEqual(decoded.command_id, "c1")


if __name__ == "__main__":
    unittest.main()
