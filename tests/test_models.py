import unittest
from datetime import datetime, timedelta
from random import randint
from hydraChess.models import Model, LockableModel, User, Game
from redis import Redis, ConnectionPool, exceptions
from chess import Board


def gen_random_id() -> int:
    return randint(0, 10 ** 9)


class TestModel(unittest.TestCase):
    def setUp(self):
        self.pool = ConnectionPool(host='localhost', port=6379, db=1)
        self.redis = Redis(connection_pool=self.pool)
        self.used_model_ids = list()
        self.class_name = "test_model_class"

    def test_fetch_push(self):
        model_id = gen_random_id()
        self.used_model_ids.append(model_id)
        model = Model(self.class_name, model_id, self.redis)
        model["test"] = "ok"
        model.push()
        model.fetch()
        self.assertEqual(model["test"], "ok")

    def test_key_error(self):
        model_id = gen_random_id()
        self.used_model_ids.append(model_id)
        model = Model(self.class_name, model_id, self.redis)
        with self.assertRaises(KeyError):
            model["nonexistent"]

    def test_multiple_update(self):
        model_id = gen_random_id()
        self.used_model_ids.append(model_id)
        model = Model(self.class_name, model_id, self.redis)

        model["test0"] = "0"
        model["test1"] = "1"
        model["test2"] = "2"

        model.push()
        model.fetch()

        self.assertEqual(model["test0"], "0")
        self.assertEqual(model["test1"], "1")
        self.assertEqual(model["test2"], "2")

    def test_delete(self):
        model_id = gen_random_id()
        model = Model(self.class_name, model_id, self.redis)

        key = model.key

        model["test"] = "ok"
        model.push()
        model.delete()

        self.assertEqual(self.redis.exists(key), 0)

    def tearDown(self):
        for id in self.used_model_ids:
            model = Model(self.class_name, id, self.redis)
            model.delete()
        self.used_model_ids.clear()


class TestLockableModel(unittest.TestCase):
    def setUp(self):
        self.pool = ConnectionPool(host='localhost', port=6379, db=1)
        self.redis = Redis(connection_pool=self.pool)
        self.used_lockable_model_ids = list()
        self.class_name = "test_lockable_model_class"

    def test_lock(self):
        lockable_model_id = gen_random_id()
        self.used_lockable_model_ids.append(lockable_model_id)
        lockable_model = LockableModel(
            self.class_name,
            lockable_model_id,
            self.redis)

        lock = self.redis.lock(f"{lockable_model.key}_lock")
        self.assertFalse(lock.acquire(blocking=False))

    def tearDown(self):
        for id in self.used_lockable_model_ids:
            lockable_model = LockableModel(self.class_name, id, self.redis)
            lockable_model.delete()
        self.used_lockable_model_ids.clear()


class TestUser(unittest.TestCase):
    def setUp(self):
        self.pool = ConnectionPool(host='localhost', port=6379, db=1)
        self.redis = Redis(connection_pool=self.pool)
        self.used_user_ids = list()

    def test_new_user_id(self):
        for expected_id in range(1, 10):
            new_user_id = User.create_new_user(self.redis)
            self.assertEqual(expected_id, new_user_id)
            self.used_user_ids.append(new_user_id)

    def test_default_values(self):
        user_id = User.create_new_user(self.redis)
        self.used_user_ids.append(user_id)
        user = User(user_id, self.redis)

        self.assertTrue(user.check_password(""))
        self.assertEqual(user.nickname, "")
        self.assertEqual(user.rating, 1200)
        self.assertEqual(user.games_cnt, 0)
        self.assertEqual(user.cur_game_id, 0)
        self.assertEqual(user.k_factor, 40)
        self.assertEqual(user.in_search, False)
        self.assertEqual(user.sid, "")
        self.assertEqual(user.avatar_hash, "default")

    def test_nickname(self):
        user_id = User.create_new_user(self.redis)
        self.used_user_ids.append(user_id)
        user = User(user_id, self.redis)

        user.nickname = "test"
        user.push()
        user.fetch()

        self.assertEqual(user.nickname, "test")

    def test_rating(self):
        user_id = User.create_new_user(self.redis)
        self.used_user_ids.append(user_id)
        user = User(user_id, self.redis)

        user.rating = 4000
        user.push()
        user.fetch()

        self.assertEqual(user.rating, 4000)

    def test_games_cnt(self):
        user_id = User.create_new_user(self.redis)
        self.used_user_ids.append(user_id)
        user = User(user_id, self.redis)

        user.games_cnt = 4000
        user.push()
        user.fetch()

        self.assertEqual(user.games_cnt, 4000)

    def test_cur_game_id_and_is_playing(self):
        user_id = User.create_new_user(self.redis)
        self.used_user_ids.append(user_id)
        user = User(user_id, self.redis)

        user.cur_game_id = 4000
        user.push()
        user.fetch()

        self.assertEqual(user.cur_game_id, 4000)
        self.assertTrue(user.is_playing())

        user.cur_game_id = 0
        user.push()
        user.fetch()
        self.assertFalse(user.is_playing())

    def test_k_factor(self):
        user_id = User.create_new_user(self.redis)
        self.used_user_ids.append(user_id)
        user = User(user_id, self.redis)

        user.k_factor = 4000
        user.push()
        user.fetch()

        self.assertEqual(user.k_factor, 4000)

    def test_in_search(self):
        user_id = User.create_new_user(self.redis)
        self.used_user_ids.append(user_id)
        user = User(user_id, self.redis)

        for val in (False, True):
            user.in_search = val
            user.push()
            user.fetch()
            self.assertEqual(user.in_search, val)

    def test_sid(self):
        user_id = User.create_new_user(self.redis)
        self.used_user_ids.append(user_id)
        user = User(user_id, self.redis)

        user.sid = "test"
        user.push()
        user.fetch()

        self.assertEqual(user.sid, "test")

    def test_user_id_by_nickname(self):
        for i in range(10):
            nonexistent_nickname = str(gen_random_id())
            user_id = User.get_user_id_by_nickname(
                nonexistent_nickname,
                self.redis)
            self.assertEqual(user_id, 0)

        user_ids = []
        for i in range(1, 11):
            user_id = User.create_new_user(self.redis)
            self.used_user_ids.append(user_id)
            user_ids.append(user_id)
            user = User(user_id, self.redis)
            user.nickname = f"test{i}"
            user.push()

        for user_id in user_ids:
            user = User(user_id, self.redis)
            expected_user_id = user_id
            actual_user_id = User.get_user_id_by_nickname(
                user.nickname,
                self.redis)
            self.assertEqual(expected_user_id, actual_user_id)

        user_id = User.create_new_user(self.redis)
        self.used_user_ids.append(user_id)
        user = User(user_id, self.redis)
        user.nickname = "test_before"
        user.push()
        user.nickname = "test_after"
        user.push()

        result = User.get_user_id_by_nickname("test_before", self.redis)
        self.assertEqual(result, 0)

        result = User.get_user_id_by_nickname("test_after", self.redis)
        self.assertEqual(result, user.id)

    def test_avatar_hash(self):
        user_id = User.create_new_user(self.redis)
        self.used_user_ids.append(user_id)
        user = User(user_id, self.redis)

        user.avatar_hash = "test"
        user.push()
        user.fetch()

        self.assertEqual(user.avatar_hash, "test")

    def tearDown(self):
        for id in self.used_user_ids:
            user = User(id, self.redis)
            user.delete()
        self.used_user_ids.clear()
        self.redis.delete("UserID")


class TestGame(unittest.TestCase):
    def setUp(self):
        self.pool = ConnectionPool(host='localhost', port=6379, db=1)
        self.redis = Redis(connection_pool=self.pool)
        self.used_game_ids = list()
        self.used_user_ids = list()

    def test_new_game_id(self):
        for expected_id in range(1, 10):
            new_game_id = Game.create_new_game(self.redis)
            self.assertEqual(expected_id, new_game_id)
            self.used_game_ids.append(new_game_id)

    def test_default_values(self):
        game_id = Game.create_new_game(self.redis)
        game = Game(game_id, self.redis)
        self.used_game_ids.append(game_id)

        self.assertEqual(game.black_user_id, 0)
        self.assertEqual(game.white_user_id, 0)
        self.assertEqual(game.black_rating_before, 0)
        self.assertEqual(game.white_rating_before, 0)
        self.assertEqual(game.state, Game.State.NOT_STARTED)
        self.assertEqual(game.result, Game.Result.NOT_DETERMINED)
        self.assertEqual(game.draw_offer_sender, Game.Color.NONE)
        self.assertEqual(game.last_move_datetime, datetime.min)
        self.assertEqual(game.total_time, timedelta(seconds=0))
        self.assertEqual(game.black_clock, timedelta(seconds=0))
        self.assertEqual(game.white_clock, timedelta(seconds=0))
        self.assertEqual(game.moves, [])

    def test_white_user_id_and_black_user_id(self):
        game_id = Game.create_new_game(self.redis)
        game = Game(game_id, self.redis)
        self.used_game_ids.append(game_id)

        game.white_user_id = 13
        game.black_user_id = 14
        game.push()
        game.fetch()

        self.assertEqual(game.white_user_id, 13)
        self.assertEqual(game.black_user_id, 14)

    def test_white_rating_before_and_black_rating_before(self):
        game_id = Game.create_new_game(self.redis)
        game = Game(game_id, self.redis)
        self.used_game_ids.append(game_id)

        game.white_rating_before = 3999
        game.black_rating_before = 4000
        game.push()
        game.fetch()

        self.assertEqual(game.white_rating_before, 3999)
        self.assertEqual(game.black_rating_before, 4000)

    def test_white_user_and_black_user(self):
        white_user_id = User.create_new_user(self.redis)
        self.used_user_ids.append(white_user_id)
        white_user = User(white_user_id, self.redis)

        black_user_id = User.create_new_user(self.redis)
        self.used_user_ids.append(black_user_id)
        black_user = User(black_user_id, self.redis)

        white_user.rating = 3999
        white_user.push()
        black_user.rating = 4000
        black_user.push()

        game_id = Game.create_new_game(self.redis)
        self.used_game_ids.append(game_id)
        game = Game(game_id, self.redis)

        game.white_user = white_user
        game.black_user = black_user
        game.push()
        game.fetch()

        self.assertEqual(game.white_user_id, white_user.id)
        self.assertEqual(game.white_rating_before, white_user.rating)

        self.assertEqual(game.black_user_id, black_user.id)
        self.assertEqual(game.black_rating_before, black_user.rating)

    def test_state(self):
        game_id = Game.create_new_game(self.redis)
        self.used_game_ids.append(game_id)
        game = Game(game_id, self.redis)

        for state in Game.State:
            game.state = state
            game.push()
            game.fetch()
            self.assertEqual(game.state, state)

    def test_result(self):
        game_id = Game.create_new_game(self.redis)
        self.used_game_ids.append(game_id)
        game = Game(game_id, self.redis)

        for result in Game.Result:
            game.result = result
            game.push()
            game.fetch()
            self.assertEqual(game.result, result)

    def test_draw_offer_sender(self):
        game_id = Game.create_new_game(self.redis)
        self.used_game_ids.append(game_id)
        game = Game(game_id, self.redis)

        for color in Game.Color:
            game.draw_offer_sender = color
            game.push()
            game.fetch()
            self.assertEqual(game.draw_offer_sender, color)

    def test_last_move_datetime(self):
        game_id = Game.create_new_game(self.redis)
        self.used_game_ids.append(game_id)
        game = Game(game_id, self.redis)

        dtime = datetime(1, 1, 1, 12, 14, 32, 312321)

        game.last_move_datetime = dtime
        game.push()
        game.fetch()
        self.assertEqual(game.last_move_datetime, dtime)

    def test_total_time_and_black_clock_and_white_clock(self):
        game_id = Game.create_new_game(self.redis)
        self.used_game_ids.append(game_id)
        game = Game(game_id, self.redis)

        total_time = timedelta(seconds=30, microseconds=13231)
        game.total_time = total_time
        black_clock = timedelta(seconds=310, microseconds=321312)
        game.black_clock = black_clock
        white_clock = timedelta(seconds=312, microseconds=31231)
        game.white_clock = white_clock

        game.push()
        game.fetch()

        self.assertEqual(game.total_time, total_time)
        self.assertEqual(game.black_clock, black_clock)
        self.assertEqual(game.white_clock, white_clock)

    def test_moves(self):
        game_id = Game.create_new_game(self.redis)
        self.used_game_ids.append(game_id)
        game = Game(game_id, self.redis)

        moves = ['e4', 'e5', 'Nf3', 'Nc6']
        game.moves = moves
        game.push()
        game.fetch()

        self.assertEqual(game.moves, moves)

    def test_moves_cnt_and_next_to_move_and_append_move(self):
        game_id = Game.create_new_game(self.redis)
        self.used_game_ids.append(game_id)
        game = Game(game_id, self.redis)

        moves = ['e4', 'e5', 'Nf3', 'Nc6']

        next_to_move = Game.Color.WHITE

        for i in range(len(moves)):
            self.assertEqual(game.get_moves_cnt(), i)
            self.assertEqual(game.get_next_to_move(), next_to_move)

            game.append_move(moves[i])
            if next_to_move == Game.Color.WHITE:
                next_to_move = Game.Color.BLACK
            else:
                next_to_move = Game.Color.WHITE

        self.assertEqual(game.get_next_to_move(), next_to_move)
        self.assertEqual(game.get_moves_cnt(), len(moves))
        self.assertEqual(game.moves, moves)

    def test_get_board(self):
        game_id = Game.create_new_game(self.redis)
        self.used_game_ids.append(game_id)
        game = Game(game_id, self.redis)

        moves = ['e4', 'e5', 'Nf3', 'Nc6']

        expected_board = Board()
        for move in moves:
            expected_board.push_san(move)

        game.moves = moves
        game.push()
        game.fetch()

        self.assertEqual(game.get_board(), expected_board)

    def tearDown(self):
        for id in self.used_game_ids:
            game = Game(id, self.redis)
            game.delete()
        self.used_game_ids.clear()

        for id in self.used_user_ids:
            user = User(id, self.redis)
            user.delete()
        self.used_user_ids.clear()

        self.redis.delete("UserID")
        self.redis.delete("GameID")


if __name__ == "__main__":
    unittest.main()
