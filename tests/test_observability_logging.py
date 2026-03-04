import io
import json
import logging
import unittest
from pathlib import Path
import sys

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from chess_punisher.observability.logging import JsonFormatter, bind_correlation_id


class ObservabilityLoggingTests(unittest.TestCase):
    def test_json_formatter_includes_correlation_id(self) -> None:
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonFormatter())

        logger = logging.getLogger("test.observability")
        logger.handlers.clear()
        logger.propagate = False
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        with bind_correlation_id("abc123"):
            logger.info("hello", extra={"foo": "bar"})

        payload = json.loads(stream.getvalue().strip())
        self.assertEqual(payload["msg"], "hello")
        self.assertEqual(payload["correlation_id"], "abc123")
        self.assertEqual(payload["foo"], "bar")


if __name__ == "__main__":
    unittest.main()
