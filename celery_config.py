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
    'on_connect': {'queue': 'normal'},
    # -- LOW PRIORITY QUEUE -- #
    'send_message': {'queue': 'low'},
    'update_k_factor': {'queue': 'low'},
    'on_disconnect': {'queue': 'low'},
    'update_rating': {'queue': 'low'},
    'make_draw_offer': {'queue': 'low'},
    # -- SEARCH QUEUE -- #
    'search_game': {'queue': 'search'},
    'cancel_search': {'queue': 'search'}
}
