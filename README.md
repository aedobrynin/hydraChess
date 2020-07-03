# Hydra Chess

Hydra Chess is a Flask application to play chess online
Tested on Python 3.7.5 and Redis 5.0.5

![Interface](https://github.com/hashlib/hydraChess/blob/master/static/img/hydra_chess.png)

## Prerequisites

1. Create new Python venv and install requirements.
```
$ python3 -mvenv dev
$ source dev/bin/activate
$ pip3 install -r requirements.txt
```
For PyPy
```
$ pypy3 -mvenv dev_pypy
$ source dev_pypy/bin/activate
$ pip3 install -r requirements_pypy.txt
```

2. Install Redis
```
$ sudo apt install redis
```

## Running
**You can run everything using scripts if:**
1. Your env is in "dev" directory ("dev_pypy" for PyPy)
2. You didn't changed scripts directory name (scripts).

**You have 2 possible ways to run everything using scripts:**
1. Run it in 5 separate terminals using ```scripts/run_all_gnome_terminal.sh```
2. Run it in one tmux window using ```scripts/run_all_tmux.sh``` (tmux must be installed)

Use ```scripts/run_all_gnome_terminal.sh pypy``` or ```scripts/run_all_tmux.sh pypy``` for PyPy.

In tmux everything looks like this:
![tmux](https://user-images.githubusercontent.com/43320720/79076597-11313480-7d04-11ea-8d25-51568a28e69d.png)


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

## Libraries used

* [chess.js](https://github.com/jhlywa/chess.js) - Used to check moves and game state on client side.
* [chessboard.js](https://github.com/hashlib/chessboardjs/) (Own fork) - Client side chess board
* [Celery](https://github.com/celery/celery) - Used to run different tasks on server side
* [Flask](https://github.com/pallets/flask) - Main server side framework
* [rom](https://github.com/josiahcarlson/rom) - Redis object mapper
