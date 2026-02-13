import unittest
from pathlib import Path
import sys

import chess.engine

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from chess_punisher.engine.blunder_classifier import Thresholds, classify_cp_loss, cp_loss


class BlunderClassifierTests(unittest.TestCase):
    def test_classification_thresholds(self) -> None:
        self.assertEqual(classify_cp_loss(0), "OK")
        self.assertEqual(classify_cp_loss(50), "INACCURACY")
        self.assertEqual(classify_cp_loss(150), "MISTAKE")
        self.assertEqual(classify_cp_loss(300), "BLUNDER")

    def test_custom_thresholds(self) -> None:
        thresholds = Thresholds(inaccuracy=20, mistake=60, blunder=120)
        self.assertEqual(classify_cp_loss(59, thresholds=thresholds), "INACCURACY")
        self.assertEqual(classify_cp_loss(60, thresholds=thresholds), "MISTAKE")

    def test_cp_loss_from_ints(self) -> None:
        self.assertEqual(cp_loss(120, 80), 40)
        self.assertEqual(cp_loss(50, 100), 0)

    def test_cp_loss_with_mate_scores(self) -> None:
        before = chess.engine.Mate(+3)
        after = chess.engine.Mate(-2)
        self.assertEqual(cp_loss(before, after), 19_995)


if __name__ == "__main__":
    unittest.main()
