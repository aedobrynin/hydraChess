from threading import Thread
import re
from time import sleep, time
from requests import Session
from random import choice, seed
from string import ascii_letters, digits
import chess
import socketio


ROOT_URL = "http://c67344bf.ngrok.io"


def gen_login(length=8):
    login = ''.join([choice(ascii_letters) for _ in range(length)])
    return login


def gen_password(length=8):
    passwd = ''.join([choice(ascii_letters + digits) for _ in range(length)])
    return passwd


class Bot(Thread):
    def __init__(self):
        seed(time())
        Thread.__init__(self)

        self.sio = socketio.Client()
        self.session = Session()
        self.board = None

        self.sio.on('game_started', self.on_game_started)
        self.sio.on('game_updated', self.on_game_updated)
        self.sio.on('game_ended', self.on_game_ended)

        self.color = None

    def run(self):
        self.register()
        # We're authomatically logged in after registration.
        # There is no need to do this.

        cookies = ';'.join(map(lambda x: f"{x[0]}={x[1]}",
                               self.session.cookies.get_dict().items()))

        self.sio.connect(ROOT_URL, headers={'Cookie': cookies})
        self.start_search()
        self.sio.wait()

    def register(self):
        url = f"{ROOT_URL}/register"

        response = self.session.get(url)

        find_token = re.search(r'"csrf_token" type="hidden" value="([^"]*)"',
                               str(response.content))
        csrf_token = find_token.groups()[0]

        login = gen_login()
        password = gen_password()
        
        self._name = f"{login}:{password}"


        data = {'login': login,
                'password': password,
                'csrf_token': csrf_token}
        data['confirm_password'] = data['password']

        response = self.session.post(url, data=data)
        assert response.url.rsplit('/', 1)[1] == 'play'

    def start_search(self):
        self.sio.emit('search', {'minutes': 5})

    def on_game_started(self, data):
        self.board = chess.Board(data['fen'])

        self.color = data['color'] == 'w'
        if self.color == chess.WHITE:
            sleep(1)
            self.make_move()

    def make_move(self):
        possible_moves = list(self.board.legal_moves)
        move = choice(possible_moves)
        self.sio.emit('make_move', {"san": self.board.san(move)})

    def on_game_updated(self, data):
        self.board.push_san(data['san'])

        if self.board.is_game_over():
            self.start_search()
        elif self.color == self.board.turn:
            sleep(5)
            self.make_move()

    def on_game_ended(self, data):
        sleep(1)
        self.start_search()


BOTS_QUANTITY = 50

if __name__ == "__main__":
    threads = list()
    for i in range(BOTS_QUANTITY):
        threads.append(Bot())

    print("Bots're ready")

    for i, thread in enumerate(threads):
        if i % 5 == 0 and i:
            sleep(10)
        else:
            sleep(2)
        thread.start()
        print(f"started: {i + 1}/{BOTS_QUANTITY}")

    print("Bots're started")

    for thread in threads:
        thread.join()
