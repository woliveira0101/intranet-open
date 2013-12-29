from intranet3 import redis
from intranet3.decorators import classproperty

class Queue(object):
    """An abstract FIFO queue"""
    __PREFIX = 'queue:'
    QUEUE_ID = None

    @classproperty
    def ID(cls):
        return cls.__PREFIX + cls.QUEUE_ID

    @classmethod
    def push(cls, element):
        """Push an element to the tail of the queue"""
        redis.lpush(cls.ID, element)

    @classmethod
    def pop(cls):
        """Pop an element from the head of the queue"""
        popped_element = redis.rpop(cls.ID)
        return popped_element
