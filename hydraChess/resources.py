from flask_restful import Resource, reqparse
from hydraChess.models import User, Game


parser = reqparse.RequestParser()
parser.add_argument('nickname', type=str, required=True)
parser.add_argument('start_from', type=int, default=0)
parser.add_argument('size', type=int, default=10, choices=(10, 20, 50, 100))


class GamesList(Resource):
    def get(self):
        args = parser.parse_args()
        nickname = args['nickname']
        start_from = args['start_from']
        size = args['size']

        user = User.get_by(login=args['nickname'])
        if not user:
            return {"message": "User doesn't exist"}, 400

        game_ids = user.game_ids[start_from: start_from + size]
        games = list()
        for game in Game.get(game_ids):
            cur_game = {
                'white_player': game.white_user.login,
                'black_player':game.black_user.login,
                'id': game.id,
                'result': game.result,
            }
            games.append(cur_game)

        return games, 200
