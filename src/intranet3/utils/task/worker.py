import requests
from .taskqueue import TaskQueue

from intranet3 import config
from intranet3.log import DEBUG_LOG, ERROR_LOG

DEBUG = DEBUG_LOG(__name__)
ERROR = ERROR_LOG(__name__)

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
        try:
            response = requests.post(
                self.task_url_prefix + task.url,
                data=task.payload,
                headers=self.headers,
                timeout=600,
            )
        except Exception as e:
            ERROR('Task %s failed %s' % (task, e))
        else:
            code = response.status_code
            if 200 <= code < 300:
                DEBUG('Task %s executed sucessfuly' % task)
            else:
                ERROR('Task %s failed with status %s' % (task, code))
        #TODO retry ?

worker = Worker()
