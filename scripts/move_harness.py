"""Interactive move harness for blunder classification."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sys

import chess
import chess.engine

# Keep the script runnable without requiring editable install first.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from chess_punisher.engine.blunder_classifier import (
    MATE_CP_EQUIVALENT,
    Thresholds,
    classify_cp_loss,
    compute_cp_loss_for_mover,
)
from chess_punisher.comms.punisher import PunishEvent, Punisher
from chess_punisher.actuation import (
    MqttActuatorAdapter,
    MqttCommandTracker,
    PahoAckTransport,
    PunishCommand,
)
from chess_punisher.logging.game_logger import GameLogger, MoveLogEntry, format_entry
from chess_punisher.observability import bind_correlation_id, configure_logging, get_logger
from chess_punisher.orchestrator import AppStateMachine, Event, event
from chess_punisher.sim import EspActuatorSim

LOGGER = get_logger(__name__)


def _stockfish_path() -> Path:
    return Path(os.getenv("STOCKFISH_PATH", "./bin/stockfish"))


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _pulse_ms_for_severity(severity: str) -> int:
    if severity == "BLUNDER":
        return 250
    if severity == "MISTAKE":
        return 180
    if severity == "INACCURACY":
        return 120
    return 100


def _build_command(
    game_id: str,
    seq: int,
    severity: str,
    move_uci: str,
) -> PunishCommand:
    command_id = f"{game_id}-{seq:04d}-{move_uci}"
    return PunishCommand(
        command_id=command_id,
        game_id=game_id,
        seq=seq,
        action="tap",
        severity=severity,
        pulse_ms=_pulse_ms_for_severity(severity),
        ttl_ms=3000,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def _evaluate_cp_for_color(
    board: chess.Board,
    color: chess.Color,
    engine: chess.engine.SimpleEngine,
    time_limit_s: float,
) -> int:
    info = engine.analyse(board, chess.engine.Limit(time=time_limit_s))
    raw_score = info.get("score")
    if raw_score is None:
        raise RuntimeError("Engine analysis did not return a score.")
    score = raw_score.pov(color)
    return score.score(mate_score=MATE_CP_EQUIVALENT)


def _parse_thresholds(raw: str) -> Thresholds:
    try:
        inaccuracy, mistake, blunder = [int(x.strip()) for x in raw.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "thresholds must be three comma-separated integers like 50,150,300"
        ) from exc
    return Thresholds(inaccuracy=inaccuracy, mistake=mistake, blunder=blunder)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Interactive move classification harness.")
    parser.add_argument("--time", type=float, default=0.1, help="Engine think time in seconds.")
    parser.add_argument(
        "--thresholds",
        type=_parse_thresholds,
        default=Thresholds(),
        help="Centipawn thresholds inaccuracy,mistake,blunder (default: 50,150,300).",
    )
    parser.add_argument(
        "--actuation-mode",
        choices=("http", "sim", "mqtt"),
        default=os.getenv("ACTUATION_MODE", "http"),
        help="Punishment transport mode (default: http).",
    )
    parser.add_argument(
        "--mqtt-host",
        default=os.getenv("MQTT_HOST", "127.0.0.1"),
        help="MQTT host when using --actuation-mode mqtt.",
    )
    parser.add_argument(
        "--mqtt-port",
        type=int,
        default=_env_int("MQTT_PORT", 1883),
        help="MQTT port when using --actuation-mode mqtt.",
    )
    parser.add_argument(
        "--mqtt-device-id",
        default=os.getenv("MQTT_DEVICE_ID", "esp32-1"),
        help="Actuator device id for protocol topics.",
    )
    parser.add_argument(
        "--mqtt-client-id",
        default=os.getenv("MQTT_CLIENT_ID", "chess-punisher-pi"),
        help="MQTT client id for Pi adapter.",
    )
    parser.add_argument(
        "--ack-timeout",
        type=float,
        default=_env_float("MQTT_ACK_TIMEOUT", 0.6),
        help="ACK timeout in seconds for sim/mqtt modes.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=_env_int("MQTT_MAX_RETRIES", 3),
        help="Max retries for sim/mqtt modes.",
    )
    return parser


def main() -> int:
    configure_logging()
    args = _build_parser().parse_args()
    board = chess.Board()
    thresholds: Thresholds = args.thresholds
    time_limit_s: float = args.time
    default_thresholds = Thresholds()
    stockfish_path = _stockfish_path()
    punisher = Punisher(
        white_url=os.getenv("PUNISHER_WHITE_URL"),
        black_url=os.getenv("PUNISHER_BLACK_URL"),
        dry_run=_env_bool("PUNISHER_DRY_RUN", default=False),
        timeout_s=0.3,
    )
    logger = GameLogger(log_path=os.getenv("GAME_LOG_PATH"))
    machine = AppStateMachine()
    game_id = f"harness-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    tracker: MqttCommandTracker | None = None
    if args.actuation_mode in {"sim", "mqtt"}:
        tracker = MqttCommandTracker(
            ack_timeout_s=args.ack_timeout,
            max_attempts=args.max_retries,
        )

    sim: EspActuatorSim | None = None
    if args.actuation_mode == "sim":
        sim = EspActuatorSim()

    mqtt_adapter: MqttActuatorAdapter | None = None
    if args.actuation_mode == "mqtt":
        try:
            transport = PahoAckTransport(
                host=args.mqtt_host,
                port=args.mqtt_port,
                device_id=args.mqtt_device_id,
                client_id=args.mqtt_client_id,
            )
        except RuntimeError as exc:
            print(f"MQTT setup error: {exc}")
            return 1
        assert tracker is not None
        mqtt_adapter = MqttActuatorAdapter(
            device_id=args.mqtt_device_id,
            tracker=tracker,
            transport=transport,
        )

    def emit(evt: Event) -> None:
        transition = machine.handle(evt)
        LOGGER.info(
            "state_transition",
            extra={
                "event": evt.type,
                "from_state": transition.previous.value,
                "to_state": transition.current.value,
                "reason": transition.reason,
            },
        )

    def dispatch_punishment(punish_evt: PunishEvent, seq: int) -> bool:
        if args.actuation_mode == "http":
            punisher.trigger(punish_evt)
            return True

        assert tracker is not None
        command = _build_command(
            game_id=game_id,
            seq=seq,
            severity=punish_evt.severity,
            move_uci=punish_evt.move_uci,
        )
        LOGGER.info(
            "punish_command_built",
            extra={
                "command_id": command.command_id,
                "mode": args.actuation_mode,
                "severity": command.severity,
            },
        )

        if args.actuation_mode == "sim":
            assert sim is not None
            tracker.register(command)
            executed = False
            for ack in sim.execute(command):
                if tracker.mark_ack(ack):
                    executed = True
            return executed

        assert mqtt_adapter is not None
        return mqtt_adapter.send_and_wait(command)

    if not stockfish_path.exists():
        print(
            f"Engine error: Stockfish binary not found at '{stockfish_path}'. "
            "Set STOCKFISH_PATH or place the binary at ./bin/stockfish."
        )
        return 1

    print(
        "Enter UCI moves (e.g. e2e4). Commands: reset, log, clearlog, quit "
        f"[actuation={args.actuation_mode}]"
    )
    with bind_correlation_id() as correlation_id:
        LOGGER.info(
            "move_harness_started",
            extra={"correlation_id": correlation_id, "actuation_mode": args.actuation_mode},
        )
        emit(event("START"))
        emit(event("CALIBRATION_STABLE", confidence=1.0))
        try:
            with chess.engine.SimpleEngine.popen_uci(str(stockfish_path)) as engine:
                command_seq = 0
                while True:
                    raw = input("> ").strip().lower()
                    if raw == "quit":
                        LOGGER.info("move_harness_quit")
                        return 0
                    if raw == "reset":
                        board.reset()
                        logger.reset()
                        LOGGER.info("board_reset")
                        emit(event("DESYNC"))
                        emit(event("START"))
                        emit(event("CALIBRATION_STABLE", confidence=1.0))
                        print("Board reset.")
                        continue
                    if raw == "log":
                        for entry in logger.tail(10):
                            print(format_entry(entry))
                        continue
                    if raw == "clearlog":
                        logger.reset()
                        LOGGER.info("log_cleared")
                        print("Log cleared.")
                        continue
                    if not raw:
                        continue

                    try:
                        move = chess.Move.from_uci(raw)
                    except ValueError:
                        LOGGER.warning("invalid_move_text", extra={"raw": raw})
                        print(f"Invalid UCI move: {raw}")
                        continue
                    if move not in board.legal_moves:
                        LOGGER.warning("illegal_move", extra={"move_uci": raw})
                        print(f"Illegal move: {raw}")
                        continue

                    emit(event("MOVE_CANDIDATE", move_uci=move.uci(), confidence=1.0))

                    mover_color = board.turn
                    mover_name = "white" if mover_color == chess.WHITE else "black"

                    try:
                        eval_before = _evaluate_cp_for_color(
                            board, mover_color, engine, time_limit_s
                        )
                        suggested = engine.play(
                            board, chess.engine.Limit(time=time_limit_s)
                        ).move
                        if suggested is None:
                            raise RuntimeError("Engine did not return a move.")
                    except RuntimeError as exc:
                        LOGGER.error("engine_error_pre_move", extra={"error": str(exc)})
                        print(f"Engine error: {exc}")
                        return 1

                    # Compute mover-aware loss/classification through shared classifier utility.
                    try:
                        loss, label = compute_cp_loss_for_mover(
                            board_before=board,
                            move=move,
                            engine=engine,
                            time_limit_s=time_limit_s,
                        )
                    except ValueError as exc:
                        LOGGER.warning("illegal_move_rejected", extra={"error": str(exc)})
                        print(f"Illegal move: {exc}")
                        continue
                    except RuntimeError as exc:
                        LOGGER.error("engine_error_post_move", extra={"error": str(exc)})
                        print(f"Engine error: {exc}")
                        return 1

                    if thresholds != default_thresholds:
                        label = classify_cp_loss(loss, thresholds=thresholds)

                    board_after = board.copy(stack=False)
                    board_after.push(move)
                    eval_after = _evaluate_cp_for_color(
                        board_after, mover_color, engine, time_limit_s
                    )

                    entry = MoveLogEntry(
                        move_uci=move.uci(),
                        mover=mover_name,
                        bestmove_uci=suggested.uci(),
                        eval_before_cp=eval_before,
                        eval_after_cp=eval_after,
                        loss_cp=loss,
                        classification=label,
                    )
                    logger.log_move(entry)
                    board.push(move)
                    LOGGER.info(
                        "move_classified",
                        extra={
                            "move_uci": entry.move_uci,
                            "mover": entry.mover,
                            "classification": entry.classification,
                            "loss_cp": entry.loss_cp,
                            "bestmove_uci": entry.bestmove_uci,
                        },
                    )

                    print(format_entry(entry))

                    if label != "OK":
                        emit(event("MOVE_CONFIRMED", punish=True))
                        command_seq += 1
                        punish_evt = PunishEvent(
                            mover=mover_name,
                            severity=label,
                            move_uci=move.uci(),
                            loss_cp=loss,
                            bestmove_uci=suggested.uci(),
                        )
                        acked = dispatch_punishment(punish_evt, seq=command_seq)
                        if acked:
                            emit(event("PUNISH_ACK"))
                        else:
                            emit(event("PUNISH_TIMEOUT"))
                    else:
                        emit(event("MOVE_CONFIRMED", punish=False))
        except OSError as exc:
            LOGGER.error(
                "engine_start_failed",
                extra={"stockfish_path": str(stockfish_path), "error": str(exc)},
            )
            print(f"Engine error: failed to start Stockfish at '{stockfish_path}': {exc}")
            return 1
        finally:
            if mqtt_adapter is not None:
                mqtt_adapter.close()


if __name__ == "__main__":
    raise SystemExit(main())
