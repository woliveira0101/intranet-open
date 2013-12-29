import requests
from .taskqueue import TaskQueue

from intranet3 import config
from intranet3.log import DEBUG_LOG

DEBUG = DEBUG_LOG(__name__)

class Worker(object):
    USER_AGENT = 'Intranet 3 Task'

    def __init__(self):
        self.task_url_prefix = config['TASK_URL']
        self.headers = {
            'User-Agent': self.USER_AGENT,
            'X-Intranet-Task': config['TASK_SECRET_KEY']
        }

    def __call__(self, time):
        task = TaskQueue.pop()
        if not task:
            return

        DEBUG('Exceuting task %s' % task)
        response = requests.post(
            self.task_url_prefix + task.url,
            data=task.payload,
            headers=self.headers
        )
        code = response.status_code
        if 200 <= code < 300:
            DEBUG('Task executed sucessfuly')
        else:
            DEBUG('Task failed with status %s' % code)
        #TODO retry ?

worker = Worker()
