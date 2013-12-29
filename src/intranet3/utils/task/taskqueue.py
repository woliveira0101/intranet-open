from intranet3.log import DEBUG_LOG

from intranet3.utils.queue import Queue
from .task import Task

DEBUG = DEBUG_LOG(__name__)

class TaskQueue(Queue):
    QUEUE_ID = 'async-tasks'

def add(url, payload=None, name='deferred'):
    task = Task(url, payload=payload, name=name)
    DEBUG('Adding task %s to queue' % task)
    TaskQueue.push(task)
    return task