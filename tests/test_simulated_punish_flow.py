import unittest
from pathlib import Path
import sys

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from chess_punisher.actuation import MqttCommandTracker
from chess_punisher.engine.blunder_classifier import classify_cp_loss
from chess_punisher.orchestrator import AppState, AppStateMachine, event
from chess_punisher.sim import EspActuatorSim
from chess_punisher.actuation.protocol import PunishCommand


class SimulatedPunishFlowTests(unittest.TestCase):
    def test_full_flow_returns_to_tracking(self) -> None:
        machine = AppStateMachine()
        machine.handle(event("START"))
        machine.handle(event("CALIBRATION_STABLE", confidence=1.0))
        machine.handle(event("MOVE_CANDIDATE", move_uci="e2e4", confidence=0.95))

        label = classify_cp_loss(350)
        self.assertEqual(label, "BLUNDER")

        machine.handle(event("MOVE_CONFIRMED", punish=(label != "OK")))
        self.assertEqual(machine.state, AppState.APPLY_PUNISHMENT)

        command = PunishCommand(
            command_id="g1-0001-e2e4",
            game_id="g1",
            seq=1,
            action="tap",
            severity=label,
            pulse_ms=250,
            ttl_ms=3000,
            created_at="2026-03-04T12:00:00Z",
        )
        tracker = MqttCommandTracker(ack_timeout_s=0.2, max_attempts=3)
        tracker.register(command)

        sim = EspActuatorSim()
        for ack in sim.execute(command):
            if tracker.mark_ack(ack):
                machine.handle(event("PUNISH_ACK"))

        self.assertEqual(machine.state, AppState.TRACKING)


if __name__ == "__main__":
    unittest.main()
