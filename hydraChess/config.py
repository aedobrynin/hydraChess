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


class ProductionConfig:
    DEBUG = False
    TESTING = False
    SECRET_KEY = "CHANGE_ME"
    REDIS_DB_ID = 0
    CELERY_BROKER_URL = f'redis://localhost:6379/{REDIS_DB_ID}'
    SOCKET_IO_URL = f'redis://localhost:6379/{REDIS_DB_ID}'
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # 4 MB
    PORT = 8000
    HOST = f"http://localhost:{PORT}/"


class TestingConfig:
    DEBUG = True
    TESTING = True
    SECRET_KEY = "ABACABADABACABA"
    REDIS_DB_ID = 1
    CELERY_BROKER_URL = f'redis://localhost:6379/{REDIS_DB_ID}'
    SOCKET_IO_URL = f'redis://localhost:6379/{REDIS_DB_ID}'
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # 4 Mb
    WTF_CSRF_ENABLED = False
    PORT = 8001
    HOST = f"http://localhost:{PORT}/"
