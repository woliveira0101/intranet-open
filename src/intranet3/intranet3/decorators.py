"""
decorators.py

Decorators for URL handlers

"""
from __future__ import with_statement
import time

from intranet3.log import INFO_LOG, EXCEPTION_LOG

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)

class classproperty(object):
     def __init__(self, getter):
         self.getter= getter
     def __get__(self, instance, owner):
         return self.getter(owner)

def log_time(func):
    def decorated_function(*args, **kwargs):
        prev = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            LOG(u"Function %s call took %f s" % (func.__name__, time.time() - prev))
    return decorated_function
