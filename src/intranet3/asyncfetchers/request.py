import gevent
from requests.auth import HTTPBasicAuth

import requests


class RPC(object):
    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = {}
        if 'data' in kwargs:
            self._kwargs['data'] = kwargs.pop('data')
        self.s = requests.Session(**kwargs)
        self._greenlet = None

    def basic_auth(self, login, password):
        self.s.auth = HTTPBasicAuth(login, password)

    def start(self):
        self._greenlet = gevent.spawn(
            self.s.request,
            *self._args,
            **self._kwargs
        )
        return self

    def get_result(self):
        self._greenlet.join()
        return self._greenlet.value