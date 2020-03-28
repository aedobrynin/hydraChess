# Hydra Chess

Hydra Chess is a Flask application to play chess online
Tested on Python 3.7.5 and RabbitMQ 3.7.8

## Getting Started

The guide is written for Linux-based systems

### Prerequisites

* Create new python venv and install requirements.
```
$ sudo apt install python3-venv python3-pip
$ python3 -mvenv dev
$ source dev/bin/activate
$ pip3 install -r requirements.txt
```

* Install rabbitmq-server
```
$ sudo apt install rabbitmq-server
```

* Create the database
```
$ export FLASK_APP='main.py' && flask db upgrade
```

### Running

* Activate the venv

```
$ source dev/bin/activate
```

* Run the rabbitmq-server
```
$ sudo service rabbitmq-server start
```

* Run the Celery worker
```
$ sudo celery -A game_management.celery worker --loglevel=info
```

* (Optional) run the Celery Flower in order to monitor tasks status
```
$ sudo celery -A game_management.celery flower --loglevel=info
```

* Run main.py
```
$ python3 main.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

## Libraries used

* [chess.js](https://github.com/jhlywa/chess.js) - Used to check moves and game state on client side.
* [chessboard.js](https://github.com/oakmac/chessboardjs/) - Client side chess board
* [Celery](https://github.com/celery/celery) - Used to run different tasks on server side
* [Flask](https://github.com/pallets/flask) - Main server side framework
* There are also different add-ons for Flask (Flask-Login, Flask-SQLAlchemy, etc...)
