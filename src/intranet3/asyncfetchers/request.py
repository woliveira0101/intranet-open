import gevent
import gevent.monkey
gevent.monkey.patch_all()

import requests


class RPC(object):
    def __init__(self, *args, **kwargs):
        self._greenlet = gevent.spawn(
            requests.request,
            *args, **kwargs
        )

    def get_result(self):
        self._greenlet.join()
        return self._greenlet.valu