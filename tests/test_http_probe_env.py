import unittest
from pathlib import Path
import sys

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from chess_punisher.comms.http_probe import health_url_from_punish_url


class HttpProbeEnvTests(unittest.TestCase):
    def test_health_url_from_punish_url(self) -> None:
        self.assertEqual(
            health_url_from_punish_url("http://192.168.1.114/punish"),
            "http://192.168.1.114/health",
        )

    def test_health_url_from_nested_punish_url(self) -> None:
        self.assertEqual(
            health_url_from_punish_url("http://esp.local/api/punish"),
            "http://esp.local/api/health",
        )


if __name__ == "__main__":
    unittest.main()
