# Hydra Chess

Hydra Chess is a Flask application to play chess online
Tested on Python 3.7.5 and Redis 5.0.5

![Interface](https://github.com/hashlib/hydraChess/blob/master/static/img/hydra_chess.png)

## Prerequisites

1. Create new python venv and install requirements.
```
$ sudo apt install python3-venv python3-pip
$ python3 -mvenv dev
$ source dev/bin/activate
$ pip3 install -r requirements.txt
```
**(Your env must be in "dev" directory in order to run everything using scripts)**

2. Install Redis
```
$ sudo apt install redis
```

## Running
**You can run everything using scripts if:**
1. Your env is in "dev" directory
2. You didn't changed root directory name (hydraChess) and scripts directory name (scripts).

If there is something different in your project, you can change scripts or [run everything manually](https://github.com/hashlib/hydraChess/blob/4098e3d8cb26400804a283a9bb4bc3910b3bb656/README.md#running).

**You have 2 possible ways to run everything using scripts:**
1. Run it in 5 separate terminals using ```scripts/run_all_gnome_terminal.sh```
2. Run it in one tmux window using ```scripts/run_all_tmux.sh``` (tmux must be installed)

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
