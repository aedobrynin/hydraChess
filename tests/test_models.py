# This file is part of the hydraChess project.
# Copyright (C) 2019-2020 Anton Dobrynin <hashlib@yandex.ru>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


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


class TestUser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rom.util.set_connection_settings(db=TestingConfig.REDIS_DB_ID)

    def setUp(self):
        self.used_user_ids = list()

    def test_game_ids_and_append_game_id(self):
        user = User()
        user.save()
        self.used_user_ids.append(user.id)

        self.assertEqual(user.game_ids, [])

        expected = []
        for game_id in range(10):
            expected.insert(0, game_id)
            user.append_game_id(game_id)
            user.save()
            user.refresh()
            self.assertEqual(expected, user.game_ids)

    def tearDown(self):
        for user_id in self.used_user_ids:
            user = User.get(user_id)
            user.delete()
        self.used_user_ids.clear()


if __name__ == "__main__":
    unittest.main()
