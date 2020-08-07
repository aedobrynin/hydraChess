from flask_restful import Resource, reqparse
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
            }
            games.append(cur_game)

        return {"games": games}, 200
