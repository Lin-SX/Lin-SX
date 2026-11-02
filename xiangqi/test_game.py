import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from game import initial, legal, apply, checked

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

if __name__ == "__main__":
    unittest.main()
