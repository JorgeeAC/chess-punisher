"""Lean orchestration state machine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .events import Event


class AppState(str, Enum):
    IDLE = "IDLE"
    CALIBRATING = "CALIBRATING"
    TRACKING = "TRACKING"
    CONFIRM_MOVE = "CONFIRM_MOVE"
    APPLY_PUNISHMENT = "APPLY_PUNISHMENT"


@dataclass
class MachineContext:
    pending_move_uci: str | None = None
    pending_punishment: bool = False
    calibration_confidence: float = 0.0
    tracking_confidence: float = 0.0
    failure_count: int = 0


@dataclass(frozen=True)
class Transition:
    previous: AppState
    current: AppState
    reason: str


class AppStateMachine:
    """Minimal explicit state machine for rapid iteration."""

    def __init__(self) -> None:
        self.state = AppState.IDLE
        self.context = MachineContext()

    def handle(self, evt: Event) -> Transition:
        previous = self.state
        reason = "ignored"

        if evt.type == "DESYNC":
            self.state = AppState.CALIBRATING
            self.context.pending_move_uci = None
            self.context.pending_punishment = False
            reason = "desync_recalibrate"
            return Transition(previous=previous, current=self.state, reason=reason)

        if self.state == AppState.IDLE:
            if evt.type == "START":
                self.state = AppState.CALIBRATING
                reason = "start"
            return Transition(previous=previous, current=self.state, reason=reason)

        if self.state == AppState.CALIBRATING:
            if evt.type == "CALIBRATION_STABLE":
                confidence = float(evt.payload.get("confidence", 0.0))
                self.context.calibration_confidence = confidence
                self.state = AppState.TRACKING
                reason = "calibration_complete"
            return Transition(previous=previous, current=self.state, reason=reason)

        if self.state == AppState.TRACKING:
            if evt.type == "MOVE_CANDIDATE":
                confidence = float(evt.payload.get("confidence", 0.0))
                move_uci = str(evt.payload.get("move_uci", ""))
                if confidence >= 0.7 and move_uci:
                    self.context.pending_move_uci = move_uci
                    self.context.tracking_confidence = confidence
                    self.state = AppState.CONFIRM_MOVE
                    reason = "candidate_detected"
            return Transition(previous=previous, current=self.state, reason=reason)

        if self.state == AppState.CONFIRM_MOVE:
            if evt.type == "MOVE_CONFIRMED":
                punish = bool(evt.payload.get("punish", False))
                self.context.pending_punishment = punish
                if punish:
                    self.state = AppState.APPLY_PUNISHMENT
                    reason = "move_confirmed_punish"
                else:
                    self.state = AppState.TRACKING
                    self.context.pending_move_uci = None
                    reason = "move_confirmed_no_punish"
            if evt.type == "MOVE_REJECTED":
                self.state = AppState.TRACKING
                self.context.pending_move_uci = None
                reason = "move_rejected"
            return Transition(previous=previous, current=self.state, reason=reason)

        if self.state == AppState.APPLY_PUNISHMENT:
            if evt.type == "PUNISH_ACK":
                self.state = AppState.TRACKING
                self.context.pending_punishment = False
                self.context.pending_move_uci = None
                self.context.failure_count = 0
                reason = "punish_ack"
            if evt.type == "PUNISH_TIMEOUT":
                self.context.failure_count += 1
                if self.context.failure_count >= 3:
                    self.state = AppState.CALIBRATING
                    reason = "punish_timeout_recalibrate"
                else:
                    reason = "punish_timeout_retry"
            return Transition(previous=previous, current=self.state, reason=reason)

        return Transition(previous=previous, current=self.state, reason=reason)
