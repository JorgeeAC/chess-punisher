"""CLI helper for direct ESP32 HTTP confirmation."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from chess_punisher.comms.http_probe import fetch_json, health_url_from_punish_url, send_http_probe


def default_url() -> str | None:
    return os.getenv("PUNISHER_WHITE_URL") or os.getenv("PUNISHER_BLACK_URL")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send a simple HTTP confirmation call to an ESP32.")
    parser.add_argument(
        "--url",
        default=default_url(),
        help="ESP32 punish endpoint, defaults to PUNISHER_WHITE_URL if set.",
    )
    parser.add_argument("--severity", default="TEST", help="Severity label sent to the ESP32.")
    parser.add_argument("--loss", type=int, default=0, help="Loss value sent to the ESP32.")
    parser.add_argument("--move", default="e2e4", help="Move label sent to the ESP32.")
    parser.add_argument("--pulse-ms", type=int, default=150, help="LED pulse width for visual confirmation.")
    parser.add_argument("--timeout", type=float, default=2.0, help="Request timeout in seconds.")
    parser.add_argument(
        "--skip-health",
        action="store_true",
        help="Skip the GET /health request and only hit /punish.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.url:
        print("HTTP probe failed: no URL provided. Set PUNISHER_WHITE_URL or pass --url.")
        return 1

    try:
        if not args.skip_health:
            health = fetch_json(health_url_from_punish_url(args.url), timeout_s=args.timeout)
            print(f"health_status={health.status}")
            print(f"health_url={health.url}")
            print(health.body)

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

    print(f"punish_status={result.status}")
    print(f"punish_url={result.url}")
    print(result.body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
