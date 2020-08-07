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


from kombu import Queue, Exchange


CELERY_QUEUES = (
    Queue('high', Exchange('high'), routing_key='high'),
    Queue('normal', Exchange('normal'), routing_key='normal'),
    Queue('low', Exchange('low'), routing_key='low'),
    Queue('search', Exchange('search'), routing_key='search')
)

CELERY_DEFAULT_QUEUE = 'normal'
CELERY_DEFAULT_EXCHANGE = 'normal'
CELERY_DEFAULT_ROUTING_KEY = 'normal'
CELERY_ROUTES = {
    # -- HIGH PRIORITY QUEUE -- #
    'make_move': {'queue': 'high'},
    'start_game': {'queue': 'high'},
    'end_game': {'queue': 'high'},
    'reconnect': {'queue': 'high'},
    'resign': {'queue': 'high'},
    'accept_draw_offer': {'queue': 'high'},
    'decline_draw_offer': {'queue': 'high'},
    'send_game_info': {'queue': 'high'},
    # -- NORMAL PRIORITY QUEUE -- #
    'on_first_move_timed_out': {'queue': 'normal'},
    'on_disconnect_timed_out': {'queue': 'normal'},
    'on_time_is_up': {'queue': 'normal'},
    # -- LOW PRIORITY QUEUE -- #
    # 'send_message': {'queue': 'low'},
    'update_k_factor': {'queue': 'low'},
    'on_disconnect': {'queue': 'low'},
    'update_rating': {'queue': 'low'},
    'make_draw_offer': {'queue': 'low'},
    # -- SEARCH QUEUE -- #
    'search_game': {'queue': 'search'},
    'cancel_search': {'queue': 'search'}
}
