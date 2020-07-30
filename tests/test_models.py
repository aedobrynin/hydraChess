import unittest
from datetime import timedelta
from chess import Board, WHITE, BLACK
import rom.util
from hydraChess.models import User, Game
from hydraChess.config import TestingConfig


class TestGame(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rom.util.set_connection_settings(db=TestingConfig.REDIS_DB_ID)

    def setUp(self):
        self.used_game_ids = list()
        self.used_user_ids = list()

    def test_total_time_and_black_clock_and_white_clock(self):
        game = Game()
        game.save()
        self.used_game_ids.append(game.id)

        total_time = timedelta(seconds=30, microseconds=13231)
        game.total_time = total_time
        black_clock = timedelta(seconds=310, microseconds=321312)
        game.black_clock = black_clock
        white_clock = timedelta(seconds=312, microseconds=31231)
        game.white_clock = white_clock

        game.save()
        game.refresh()

        self.assertEqual(game.total_time, total_time)
        self.assertEqual(game.black_clock, black_clock)
        self.assertEqual(game.white_clock, white_clock)

    def test_moves(self):
        game = Game()
        game.save()
        self.used_game_ids.append(game.id)

        moves = ['e4', 'e5', 'Nf3', 'Nc6']
        game.moves = moves
        game.save()
        game.refresh()

        self.assertEqual(game.moves, moves)

    def test_moves_cnt_and_next_to_move_and_append_move(self):
        game = Game()
        game.save()
        self.used_game_ids.append(game.id)

        moves = ['e4', 'e5', 'Nf3', 'Nc6']

        next_to_move = WHITE

        for i in range(len(moves)):
            self.assertEqual(game.get_moves_cnt(), i)
            self.assertEqual(game.get_next_to_move(), next_to_move)

            game.append_move(moves[i])
            if next_to_move == WHITE:
                next_to_move = BLACK
            else:
                next_to_move = WHITE

        self.assertEqual(game.get_next_to_move(), next_to_move)
        self.assertEqual(game.get_moves_cnt(), len(moves))
        self.assertEqual(game.moves, moves)

    def test_get_board(self):
        game = Game()
        game.save()
        self.used_game_ids.append(game.id)

        moves = ['e4', 'e5', 'Nf3', 'Nc6']

        expected_board = Board()
        for move in moves:
            expected_board.push_san(move)

        game.moves = moves
        game.save()
        game.refresh()

        self.assertEqual(game.get_board(), expected_board)

    def tearDown(self):
        for game_id in self.used_game_ids:
            game = Game.get(game_id)
            game.delete()
        self.used_game_ids.clear()

        for user_id in self.used_user_ids:
            user = User.get(user_id)
            user.delete()
        self.used_user_ids.clear()


if __name__ == "__main__":
    unittest.main()
