class ProductionConfig:
    DEBUG = False
    TESTING = False
    SECRET_KEY = "CHANGE_ME"
    REDIS_DB_ID = 0
    CELERY_BROKER_URL = f'redis://localhost:6379/{REDIS_DB_ID}'
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # 4 MB


class TestingConfig:
    DEBUG = True
    TESTING = True
    SECRET_KEY = "ABACABADABACABA"
    REDIS_DB_ID = 1
    CELERY_BROKER_URL = f'redis://localhost:6379/{REDIS_DB_ID}'
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # 4 Mb
    WTF_CSRF_ENABLED = False
