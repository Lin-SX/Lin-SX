import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from game import initial, legal, apply, checked, position_status, render_board_svg


class XiangqiRulesTests(unittest.TestCase):
    def test_initial_position_and_board_shape(self):
        state = initial()
        self.assertEqual(len(state["board"]), 10)
        self.assertTrue(all(len(row) == 9 for row in state["board"]))
        self.assertGreater(len(legal(state["board"], "r")), 0)

    def test_pawn_can_advance_but_not_move_sideways_before_crossing(self):
        moves = legal(initial()["board"], "r")
        self.assertIn((0, 6, 0, 5), moves)
        self.assertNotIn((0, 6, 1, 6), moves)

    def test_horse_leg_rule_and_opening_moves(self):
        moves = legal(initial()["board"], "r")
        self.assertIn((1, 9, 0, 7), moves)
        self.assertIn((1, 9, 2, 7), moves)
        board = [[None] * 9 for _ in range(10)]
        board[0][4] = "bK"
        board[9][4] = "rK"
        board[5][4] = "rH"
        board[5][5] = "rP"  # blocks the horse's right leg
        self.assertNotIn((4, 5, 6, 6), legal(board, "r"))

    def test_elephant_cannot_cross_river_and_elephant_eye_can_be_blocked(self):
        board = [[None] * 9 for _ in range(10)]
        board[0][4] = "bK"
        board[9][4] = "rK"
        board[6][4] = "rP"  # keep generals from facing
        board[7][2] = "rE"
        moves = legal(board, "r")
        self.assertIn((2, 7, 0, 5), moves)
        self.assertIn((2, 7, 4, 5), moves)
        board[6][3] = "rP"
        self.assertNotIn((2, 7, 4, 5), legal(board, "r"))

    def test_cannon_requires_exactly_one_screen_to_capture(self):
        board = [[None] * 9 for _ in range(10)]
        board[0][4] = "bK"
        board[9][4] = "rK"
        board[5][4] = "rP"  # keep generals from facing
        board[7][1] = "rC"
        board[4][1] = "rP"  # screen
        board[2][1] = "bH"
        self.assertIn((1, 7, 1, 2), legal(board, "r"))
        board[4][1] = None
        self.assertNotIn((1, 7, 1, 2), legal(board, "r"))

    def test_move_cannot_leave_generals_facing(self):
        board = [[None] * 9 for _ in range(10)]
        board[0][4] = "bK"
        board[9][4] = "rK"
        board[5][4] = "rR"
        self.assertNotIn((4, 5, 3, 5), legal(board, "r"))

    def test_apply_move_switches_turn_and_records_history(self):
        state = initial()
        apply(state, (0, 6, 0, 5))
        self.assertEqual(state["turn"], "b")
        self.assertEqual(state["ply"], 1)
        self.assertEqual(state["moves"][-1]["from"], "a6")
        self.assertEqual(state["moves"][-1]["to"], "a5")

    def test_facing_generals_is_check(self):
        board = [[None] * 9 for _ in range(10)]
        board[0][4] = "bK"
        board[9][4] = "rK"
        self.assertTrue(checked(board, "r"))
        self.assertTrue(checked(board, "b"))

    def test_position_status_reports_check(self):
        board = [[None] * 9 for _ in range(10)]
        board[0][4] = "bK"
        board[9][4] = "rK"
        board[2][4] = "rR"
        state, moves = position_status(board, "b")
        self.assertEqual(state, "check")
        self.assertGreater(len(moves), 0)

    def test_svg_renderer_contains_board_landmarks_and_pieces(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "board.svg"
            svg = render_board_svg(initial(), path)
            self.assertTrue(path.exists())
            self.assertIn("楚 河", svg)
            self.assertIn("汉 界", svg)
            self.assertIn("帅", svg)
            self.assertIn("将", svg)


if __name__ == "__main__":
    unittest.main()
