import unittest
from pathlib import Path
import sys

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from chess_punisher.comms.http_probe import HttpProbeResult, build_probe_url


class HttpProbeTests(unittest.TestCase):
    def test_build_probe_url(self) -> None:
        url = build_probe_url(
            url="http://192.168.1.50/punish",
            severity="TEST",
            loss_cp=0,
            move_uci="e2e4",
            pulse_ms=180,
        )
        self.assertEqual(
            url,
            "http://192.168.1.50/punish?severity=TEST&loss=0&move=e2e4&pulse_ms=180",
        )

    def test_http_probe_result_json_body(self) -> None:
        result = HttpProbeResult(
            status=200,
            url="http://192.168.1.50/punish?severity=TEST",
            body='{"ok":true,"device_id":"esp32-1"}',
        )
        payload = result.json_body()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["device_id"], "esp32-1")


if __name__ == "__main__":
    unittest.main()
