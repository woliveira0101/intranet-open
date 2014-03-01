import gevent
from requests.auth import HTTPBasicAuth

import requests


class RPC(object):
    def __init__(self, url=None, method='GET', **kwargs):
        method = method.upper()

        self.method = method
        self.url = url
        self.kwargs = kwargs

        self.s = requests.Session()
        self._greenlet = None

    def basic_auth(self, login, password):
        self.s.auth = HTTPBasicAuth(login, password)

    def start(self):
        self._greenlet = gevent.spawn(
            self.s.request,
            self.method,
            self.url,
            verify=False,
            **self.kwargs
        )
        return self

    def get_result(self):
        self._greenlet.join()

        return self._greenlet.value
