"""Interactive vision preview window for Raspberry Pi monitor."""

from __future__ import annotations

import argparse
from pathlib import Path
import time
import sys

import cv2

# Keep the script runnable without requiring editable install first.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from chess_punisher.vision import VisionPreview


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Live camera preview.")
    parser.add_argument(
        "--backend",
        choices=("auto", "picamera2", "opencv"),
        default="auto",
        help="Camera backend selection.",
    )
    parser.add_argument("--gray", type=int, default=0, help="Set to 1 for grayscale display.")
    parser.add_argument("--width", type=int, default=640, help="Frame width.")
    parser.add_argument("--height", type=int, default=480, help="Frame height.")
    parser.add_argument("--fps", type=int, default=20, help="Target capture FPS.")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    gray_mode = bool(args.gray)

    preview = VisionPreview(
        backend=args.backend,
        width=args.width,
        height=args.height,
        fps=args.fps,
    )
    print(f"[VISION] backend={preview.selected_backend} gray={int(gray_mode)}")

    window_name = "Chess Punisher Vision Preview"
    last_t = time.perf_counter()
    fps = 0.0

    try:
        for frame in preview.frames():
            now = time.perf_counter()
            dt = now - last_t
            if dt > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / dt)
            last_t = now

            if gray_mode:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                display = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                mode = "GRAY"
            else:
                display = frame
                mode = "COLOR"

            cv2.putText(
                display,
                f"FPS: {fps:5.1f}  MODE: {mode}",
                (10, 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )
            cv2.imshow(window_name, display)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
    except RuntimeError as exc:
        print(f"[VISION][ERROR] {exc}")
        return 1
    finally:
        preview.close()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
