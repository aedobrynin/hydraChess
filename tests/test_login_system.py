from gevent import monkey
monkey.patch_all()


from uuid import uuid4
from time import sleep
from html import unescape
from multiprocessing import Process
import unittest
import requests
from redis import ConnectionPool, Redis
from hydraChess.config import TestingConfig
from hydraChess.__main__ import app, sio


class TestRegister(unittest.TestCase):
    process = None
    @classmethod
    def setUpClass(cls):
        app.config.from_object(TestingConfig)
        app.config['REDIS_POOL'] = ConnectionPool(
            host='localhost',
            port=6379,
            db=app.config['REDIS_DB_ID']
        )
        app.config['REDIS_OBJ'] =\
            Redis(connection_pool=app.config['REDIS_POOL'])
        cls.process = Process(
            target=sio.run,
            args=(app,),
            kwargs={'port': 8000, 'debug': True, 'use_reloader': False}
        )
        cls.process.start()
        sleep(3)

    def setUp(self):
        self.url = 'http://localhost:8000/register'
        self.user_data = {
            'login': uuid4().hex[:15],
            'password': 'testtesttest',
            'confirm_password': 'testtesttest',
            'submit': 'Register'
        }

    def test_empty_login(self):
        data = self.user_data.copy()
        data['login'] = ''
        resp = requests.post(self.url, data=data)
        self.assertIn("This field is required.", resp.text)

    def test_too_short_login(self):
        data = self.user_data.copy()
        for login_len in range(1, 3):
            data['login'] = data['login'][:login_len]
            resp = requests.post(self.url, data=data)
            self.assertIn(
                "Login can't be shorter than 3 characters",
                unescape(resp.text)
            )

    def test_too_long_login(self):
        data = self.user_data.copy()
        for i in range(21, 25):
            data['login'] = 'a' * i
            resp = requests.post(self.url, data=data)
            self.assertIn(
                "Login can't be longer than 20 characters",
                unescape(resp.text)
            )

    def test_bad_char_in_login(self):
        data = self.user_data.copy()
        for bad_char in "   #$()$!.,<>\"@+-=|\\'ἱερογλύφος測試":
            data['login'] = 'a' * 5 + bad_char
            resp = requests.post(self.url, data=data)
            self.assertIn(
                "Only letters, digits and underscore are allowed",
                unescape(resp.text)
            )

    def test_empty_password(self):
        data = self.user_data.copy()
        data['password'] = data['confirm_password'] = ''
        resp = requests.post(self.url, data=data)
        self.assertIn(
            "This field is required",
            unescape(resp.text)
        )

    def test_too_short_password(self):
        data = self.user_data.copy()
        for password_len in range(1, 8):
            data['password'] = data['confirm_password'] = 'a' * password_len
            resp = requests.post(self.url, data=data)
            self.assertIn(
                "Password can't be shorter than 8 characters",
                unescape(resp.text)
            )

    def test_too_long_password(self):
        data = self.user_data.copy()
        for password_len in range(128, 135):
            data['password'] = data['confirm_password'] = 'a' * password_len
            resp = requests.post(self.url, data=data)
            self.assertIn(
                "Password can't be longer than 127 characters",
                unescape(resp.text)
            )

    def test_bad_char_in_password(self):
        data = self.user_data.copy()
        for bad_char in "   \"\\'ἱερογλύφος測試":
            data['password'] = data['confirm_password'] = 'a' * 10 + bad_char
            resp = requests.post(self.url, data=data)
            self.assertIn(
                "Only letters, digits and symbols are allowed",
                unescape(resp.text)
            )

    def test_bad_password_confirmation(self):
        data = self.user_data.copy()
        data['confirm_password'] = data['password'][:-1]
        resp = requests.post(self.url, data=data)
        self.assertIn(
            "Passwords must match",
            unescape(resp.text)
        )

    def test_used_login(self):
        data = self.user_data.copy()
        resp = requests.post(self.url, data=data)
        self.assertIn("lobby", resp.url)
        resp = requests.post(self.url, data=data)
        self.assertIn(
            "Login already taken",
            unescape(resp.text)
        )

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()


class TestLogin(unittest.TestCase):
    process = None
    @classmethod
    def setUpClass(cls):
        app.config.from_object(TestingConfig)
        app.config['REDIS_POOL'] = ConnectionPool(
            host='localhost',
            port=6379,
            db=app.config['REDIS_DB_ID']
        )
        app.config['REDIS_OBJ'] =\
            Redis(connection_pool=app.config['REDIS_POOL'])
        cls.process = Process(
            target=sio.run,
            args=(app,),
            kwargs={'port': 8000, 'debug': True, 'use_reloader': False}
        )
        cls.process.start()
        sleep(3)

    def setUp(self):
        self.url = 'http://localhost:8000/sign_in'
        self.user_data = {
            'login': uuid4().hex[:10],
            'password': 'testtesttest',
            'submit': 'Sign+in'
        }

        data = self.user_data.copy()
        data['submit'] = 'Register'
        data['confirm_password'] = data['password']
        resp = requests.post('http://localhost:8000/register', data=data)
        self.assertIn('lobby', resp.url)

    def test_bad_login(self):
        data = self.user_data.copy()
        data['login'] = data['login'][:-1]
        resp = requests.post(self.url, data=data)
        self.assertIn(
            "Wrong login or password",
            unescape(resp.text)
        )

    def test_wrong_password(self):
        data = self.user_data.copy()
        data['password'] = data['password'][:-1]
        resp = requests.post(self.url, data=data)
        self.assertIn(
            "Wrong login or password",
            unescape(resp.text)
        )

    def test_successful_login(self):
        data = self.user_data.copy()
        resp = requests.post(self.url, data=data)
        self.assertIn('lobby', resp.url)

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()


if __name__ == "__main__":
    unittest.main()
