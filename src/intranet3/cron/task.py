# -*- coding: utf-8 -*-
from pprint import pformat

from twisted.web.client import Agent, WebClientContextFactory
from twisted.web.http_headers import Headers
from twisted.internet import reactor

from intranet3.log import INFO_LOG, EXCEPTION_LOG, WARN_LOG
from intranet3.utils.mail import MailCheckerTask
from intranet3 import config
from failsafe import Repeater, RequiredAction

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)
WARN= WARN_LOG(__name__)

class URLCronTask(object):

    USER_AGENT = 'STXNext Intranet 2 Cron task'
    contextFactory = WebClientContextFactory()
    client = Agent(reactor, contextFactory)

    def __init__(self, task_name, url, repeats=None):
        self.busy = False
        self.task_name = task_name
        self.url = '%s%s' % (config['CRON_URL'], url)
        self.repeats = repeats
        self.repeated = 0

    def get_headers(self):
        """ Generate request headers (as a dictionary) """
        return {
            'User-Agent': [self.USER_AGENT],
            'X-Intranet-Cron': [config['CRON_SECRET_KEY']]
        }

    def request(self, url, headers, method='GET'):
        LOG(u'Will request URL %s with headers %s, method %s' % (url, pformat(headers), method))
        deferred = self.client.request(
            method,
            url,
            Headers(headers)
        )
        deferred.addCallbacks(self.on_success, self.on_failure)

    def on_failure(self, err):
        self.busy = False
        EXCEPTION(u"Cron task [%s] failed: %s" % (self.task_name, err))

    def on_success(self, resp):
        self.busy = False
        LOG(u'Cron function [%s] finished (status code %s)' % (self.task_name, resp.code))

    def __call__(self):
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

