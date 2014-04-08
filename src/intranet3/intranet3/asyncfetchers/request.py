from requests.auth import HTTPBasicAuth

import requests

from .greenlet import Greenlet


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
        self._greenlet = Greenlet.spawn(
            self.s.request,
            self.method,
            self.url,
            verify=False,
            **self.kwargs
        )
        return self

    def get_result(self):
        self._greenlet.join()
        self._greenlet.reraise_exc()

        return self._greenlet.value
