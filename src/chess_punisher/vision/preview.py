"""Live camera preview backends for Raspberry Pi and USB webcams."""

from __future__ import annotations

from typing import Generator

import cv2
import numpy as np


class VisionPreview:
    def __init__(
        self,
        backend: str = "auto",
        width: int = 640,
        height: int = 480,
        fps: int = 20,
    ) -> None:
        self.backend = backend
        self.width = width
        self.height = height
        self.fps = fps
        self._camera = None
        self._picam2 = None
        self._selected_backend = ""
        self._setup_backend()

    def _setup_backend(self) -> None:
        backend = self.backend.lower()
        if backend not in {"auto", "picamera2", "opencv"}:
            raise ValueError("backend must be one of: auto, picamera2, opencv")

        if backend in {"auto", "picamera2"} and self._try_picamera2():
            self._selected_backend = "picamera2"
            return

        if backend == "picamera2":
            raise RuntimeError("Picamera2 backend requested but unavailable.")

        if self._try_opencv():
            self._selected_backend = "opencv"
            return

        raise RuntimeError("Could not initialize camera via Picamera2 or OpenCV.")

    def _try_picamera2(self) -> bool:
        try:
            from picamera2 import Picamera2  # type: ignore
        except ImportError:
            if self.backend in {"auto", "picamera2"}:
                print("[VISION][WARN] Picamera2 not installed; falling back to OpenCV.")
            return False

        try:
            picam2 = Picamera2()
            config = picam2.create_preview_configuration(
                main={"size": (self.width, self.height), "format": "BGR888"},
                controls={"FrameRate": float(self.fps)},
            )
            picam2.configure(config)
            picam2.start()
            self._picam2 = picam2
            return True
        except Exception as exc:
            print(f"[VISION][WARN] Picamera2 init failed: {exc}. Falling back to OpenCV.")
            self._picam2 = None
            return False

    def _try_opencv(self) -> bool:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return False
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(self.width))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(self.height))
        cap.set(cv2.CAP_PROP_FPS, float(self.fps))
        self._camera = cap
        return True

    @property
    def selected_backend(self) -> str:
        return self._selected_backend

    def frames(self) -> Generator[np.ndarray, None, None]:
        while True:
            if self._selected_backend == "picamera2":
                assert self._picam2 is not None
                frame = self._picam2.capture_array()
                if frame is None:
                    continue
                if frame.ndim == 2:
                    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                yield frame
                continue

            assert self._camera is not None
            ok, frame = self._camera.read()
            if not ok or frame is None:
                continue
            yield frame

    def close(self) -> None:
        if self._picam2 is not None:
            try:
                self._picam2.stop()
                self._picam2.close()
            except Exception:
                pass
            self._picam2 = None
        if self._camera is not None:
            self._camera.release()
            self._camera = None
