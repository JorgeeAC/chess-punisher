"""CLI helper for direct ESP32 HTTP confirmation."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from chess_punisher.comms.http_probe import send_http_probe


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send a simple HTTP confirmation call to an ESP32.")
    parser.add_argument("--url", required=True, help="ESP32 punish endpoint, for example http://192.168.1.50/punish")
    parser.add_argument("--severity", default="TEST", help="Severity label sent to the ESP32.")
    parser.add_argument("--loss", type=int, default=0, help="Loss value sent to the ESP32.")
    parser.add_argument("--move", default="e2e4", help="Move label sent to the ESP32.")
    parser.add_argument("--pulse-ms", type=int, default=150, help="LED pulse width for visual confirmation.")
    parser.add_argument("--timeout", type=float, default=2.0, help="Request timeout in seconds.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = send_http_probe(
            url=args.url,
            severity=args.severity,
            loss_cp=args.loss,
            move_uci=args.move,
            pulse_ms=args.pulse_ms,
            timeout_s=args.timeout,
        )
    except OSError as exc:
        print(f"HTTP probe failed: {exc}")
        return 1

    print(f"status={result.status}")
    print(f"url={result.url}")
    print(result.body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
