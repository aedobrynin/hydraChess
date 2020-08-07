# Hydra Chess

Hydra Chess is a Flask application to play chess online
Tested on Python 3.7+ (PyPy 7.3.1+) and Redis 5.0.5
![Interface](https://raw.githubusercontent.com/hashlib/hydraChess/master/hydraChess/static/img/hydra_chess.png)
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fhashlib%2FhydraChess.svg?type=shield)](https://app.fossa.com/projects/git%2Bgithub.com%2Fhashlib%2FhydraChess?ref=badge_shield)

## Prerequisites

1. Create new Python venv and install requirements.
```
$ python3 -mvenv dev
$ source dev/bin/activate
$ pip3 install -r requirements.txt
```

2. Install Redis
```
$ sudo apt install redis
```

## Running
**You can run everything using scripts if:**
1. Your env is in "dev" directory
2. You didn't changed scripts directory name (scripts).

**You have 2 possible ways to run everything using scripts:**
1. Run it in 5 separate terminals using ```scripts/run_all_gnome_terminal.sh```
2. Run it in one tmux window using ```scripts/run_all_tmux.sh``` (tmux must be installed)

In tmux everything looks like this:
![tmux](https://user-images.githubusercontent.com/43320720/79076597-11313480-7d04-11ea-8d25-51568a28e69d.png)


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details


[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fhashlib%2FhydraChess.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Fhashlib%2FhydraChess?ref=badge_large)

## Libraries used

* [chess.js](https://github.com/jhlywa/chess.js) - Used to check moves and game state on client side.
* [chessboard.js](https://github.com/hashlib/chessboardjs/) (Own fork) - Client side chess board
* [Celery](https://github.com/celery/celery) - Used to run different tasks on server side
* [Flask](https://github.com/pallets/flask) - Main server side framework
* [rom](https://github.com/josiahcarlson/rom) - Redis object mapper