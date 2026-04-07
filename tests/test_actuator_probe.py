import unittest
from pathlib import Path
import sys

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from chess_punisher.actuation.probe import ProbeResult, build_probe_command
from chess_punisher.actuation.protocol import ActuatorStatus


class ActuatorProbeTests(unittest.TestCase):
    def test_build_probe_command_is_valid(self) -> None:
        command = build_probe_command(device_id="esp32-1", pulse_ms=180)
        self.assertEqual(command.action, "tap")
        self.assertEqual(command.pulse_ms, 180)
        self.assertIn("probe-esp32-1", command.command_id)
        command.validate()

    def test_probe_result_ok_requires_received_and_executed(self) -> None:
        result = ProbeResult(status_seen=True, received_seen=True, executed_seen=True)
        self.assertTrue(result.ok)

        incomplete = ProbeResult(status_seen=True, received_seen=True, executed_seen=False)
        self.assertFalse(incomplete.ok)

    def test_actuator_status_round_trip(self) -> None:
        status = ActuatorStatus(
            online=True,
            firmware="0.1.0",
            last_command_id="cmd-1",
            rssi=-48,
        )
        decoded = ActuatorStatus.from_json(status.to_json())
        self.assertEqual(decoded.last_command_id, "cmd-1")
        self.assertEqual(decoded.rssi, -48)


if __name__ == "__main__":
    unittest.main()
