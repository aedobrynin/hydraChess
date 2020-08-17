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


from flask_restful import Resource, reqparse
from flask_login import current_user
from hydraChess.models import User, Game


class GamesPlayed(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('nickname', type=str, required=True)

    def get(self):
        args = self.parser.parse_args()
        nickname = args['nickname']

        user = User.get_by(login=nickname)
        if not user:
            return {"message": "User doesn't exist"}, 400
        return {"games_played": user.games_played}, 200


class GamesList(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('nickname', type=str, required=True)
    parser.add_argument('start_from', type=int, default=0)
    parser.add_argument(
        'size',
        type=int,
        default=10,
        choices=(10, 20, 50, 100)
    )

    def get(self):
        args = self.parser.parse_args()
        nickname = args['nickname']
        start_from = args['start_from']
        size = args['size']

        user = User.get_by(login=nickname)
        if not user:
            return {"message": "User doesn't exist"}, 400

        game_ids = user.game_ids[start_from: start_from + size]
        games = list()
        for game in Game.get(game_ids):
            cur_game = {
                'white_player': game.white_user.login,
                'black_player': game.black_user.login,
                'id': game.id,
                'result': game.result,
                'moves_cnt': game.get_moves_cnt(),
            }
            games.append(cur_game)

        return {"games": games}, 200


class GameResource(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('id', type=int, required=True)

    def get(self):
        args = self.parser.parse_args()
        game_id = args['id']
        game = Game.get(game_id)

        if not game:
            return {"message": "Game doesn't exist"}, 400

        if not game.is_finished:
            return {
                "message": "Game isn't accessible by this way right now"
            }, 403

        game_data = dict()
        game_data["white_user"] = {
            "nickname": game.white_user.login,
            "rating": game.white_rating
        }
        game_data["black_user"] = {
            "nickname": game.black_user.login,
            "rating": game.black_rating
        }
        game_data["result"] = game.result
        game_data["moves"] = game.raw_moves

        if current_user.is_authenticated:
            if current_user.id == game.white_user.id:
                game_data['color'] = 'w'
            elif current_user.id == game.black_user.id:
                game_data['color'] = 'b'

        return {"game": game_data}, 200
