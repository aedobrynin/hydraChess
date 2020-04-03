from kombu import Queue, Exchange


CELERY_QUEUES = (
    Queue('high', Exchange('high'), routing_key='high'),
    Queue('normal', Exchange('normal'), routing_key='normal'),
    Queue('low', Exchange('low'), routing_key='low')
)

CELERY_DEFAULT_QUEUE = 'normal'
CELERY_DEFAULT_EXCHANGE = 'normal'
CELERY_DEFAULT_ROUTING_KEY = 'normal'
CELERY_ROUTES = {
    # -- HIGH PRIORITY QUEUE -- #
    'update_game': {'queue': 'high'},
    'start_game': {'queue': 'high'},
    'end_game': {'queue': 'high'},
    'on_reconnect': {'queue': 'high'},
    'update_rating': {'queue': 'high'},
    # -- NORMAL PRIORITY QUEUE -- #
    'send_message': {'queue': 'normal'},
    'on_first_move_timed_out': {'queue': 'normal'},
    'on_disconnect_timed_out': {'queue': 'normal'},
    'on_connect': {'queue': 'normal'},
    'on_disconnect': {'queue': 'normal'},
    # -- LOW PRIORITY QUEUE -- #
    'update_k_factor': {'queue': 'low'},
}
