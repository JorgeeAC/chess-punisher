import unittest
from pathlib import Path
import sys

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from chess_punisher.orchestrator import AppState, AppStateMachine, event


class StateMachineTests(unittest.TestCase):
    def test_nominal_flow_no_punishment(self) -> None:
        machine = AppStateMachine()
        machine.handle(event("START"))
        machine.handle(event("CALIBRATION_STABLE", confidence=0.95))
        machine.handle(event("MOVE_CANDIDATE", move_uci="e2e4", confidence=0.92))
        transition = machine.handle(event("MOVE_CONFIRMED", punish=False))
        self.assertEqual(machine.state, AppState.TRACKING)
        self.assertEqual(transition.reason, "move_confirmed_no_punish")

    def test_punishment_flow(self) -> None:
        machine = AppStateMachine()
        machine.handle(event("START"))
        machine.handle(event("CALIBRATION_STABLE", confidence=0.95))
        machine.handle(event("MOVE_CANDIDATE", move_uci="e2e4", confidence=0.92))
        machine.handle(event("MOVE_CONFIRMED", punish=True))
        self.assertEqual(machine.state, AppState.APPLY_PUNISHMENT)
        machine.handle(event("PUNISH_ACK"))
        self.assertEqual(machine.state, AppState.TRACKING)

    def test_timeout_recalibration(self) -> None:
        machine = AppStateMachine()
        machine.handle(event("START"))
        machine.handle(event("CALIBRATION_STABLE", confidence=1.0))
        machine.handle(event("MOVE_CANDIDATE", move_uci="d2d4", confidence=0.8))
        machine.handle(event("MOVE_CONFIRMED", punish=True))
        machine.handle(event("PUNISH_TIMEOUT"))
        machine.handle(event("PUNISH_TIMEOUT"))
        machine.handle(event("PUNISH_TIMEOUT"))
        self.assertEqual(machine.state, AppState.CALIBRATING)


if __name__ == "__main__":
    unittest.main()
