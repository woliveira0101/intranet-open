# -*- coding: utf-8 -*-
import requests

from intranet3.log import INFO_LOG, EXCEPTION_LOG, WARN_LOG, ERROR_LOG
from intranet3 import config

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)
WARN = WARN_LOG(__name__)
ERROR = ERROR_LOG(__name__)

class URLCronTask(object):

    USER_AGENT = 'STXNext Intranet 2 Cron task'

    def __init__(self, task_name, url, repeats=None):
        self.busy = False
        self.task_name = task_name
        self.url = '%s%s' % (config['CRON_URL'], url)
        self.repeats = repeats
        self.repeated = 0

    def get_headers(self):
        """ Generate request headers (as a dictionary) """
        return {
            'User-Agent': self.USER_AGENT,
            'X-Intranet-Cron': config['CRON_SECRET_KEY']
        }

    def request(self, url, headers, method='GET'):
        LOG(u'Will request URL %s with method %s' % (url, method))
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                timeout=60,
            )
        except Exception as e:
            ERROR(u'Cron function [%s] ended with failure %s' % (
                self.task_name,
                e
            ))
        else:
            if 199 < response.status_code < 300:
                LOG(u'Cron function [%s] done' % (self.task_name))
            else:
                ERROR(u'Cron function [%s] ended with failure (code %s): %s' % (
                    self.task_name,
                    response.status_code,
                    response.content,
                ))

        self.busy = False


    def __call__(self, *args, **kwargs):
        LOG(u'Cron function [%s] starting (%s)' % (self.task_name, self.repeated))
        if not self.busy:
            self.busy = True
            self.repeated = 0
            self.request(self.url, self.get_headers())
        elif (self.repeats is not None) and self.repeated >= self.repeats:
            WARN(u"Overriding busy action [%s] on %s/%s time" % (self.task_name, self.repeated, self.repeats))
            self.repeated = 0
            self.request(self.url, self.get_headers())
        else:
            self.repeated += 1
            WARN(u'Action [%s] is busy (%s/%s)' % (self.task_name, self.repeated, self.repeats))

