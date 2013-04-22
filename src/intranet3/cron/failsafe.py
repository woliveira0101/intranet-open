""" A simplistic pickle-and-file-based store for CRON urls, that failed to be executed """

import os.path
import datetime

from pickle import load, dump
from functools import partial, wraps
from twisted.web.client import Agent, WebClientContextFactory
from twisted.web.http_headers import Headers
from twisted.internet import reactor

from intranet3.log import DEBUG_LOG, EXCEPTION_LOG, INFO_LOG
from intranet3.helpers import dates_between
from intranet3.helpers import previous_day
from intranet3 import config

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)
DEBUG = DEBUG_LOG(__name__)


class RequiredAction(object):
    def __init__(self, name, url_producer):
        """
        @param name: unique ID of this action
        @param url_producer: function that produces an URL for this action from url_prefix and datetime.date
        """
        self.name = name
        self.url_producer = url_producer


class Repeater(object):
    
    USER_AGENT = 'STXNext Intranet 2 Cron task'
    contextFactory = WebClientContextFactory()
    client = Agent(reactor, contextFactory)
        
    def __init__(self, *actions):
        self.headers = {
            'User-Agent': [self.USER_AGENT],
            'X-Intranet-Cron': [config['CRON_SECRET_KEY']]
        }
        self.actions = {}
        for action in actions:
            self.actions[action.name] = action.url_producer
        self.file_path = config['REPEATER_FILE']
        
    def pending(self):
        """ returns a list of pending entries """
        result = []
        yesterday = previous_day(datetime.date.today())
        cron_url = config['CRON_URL']
        with PickleStore(self.file_path) as store:
            for date, action_name in store.get_pending(yesterday, self.actions.keys()):
                result.append(
                        ('%s%s' % (cron_url, self.actions[action_name](date)),
                         partial(self.update, date, action_name))
                )
        return result
                
    def update(self, date, action_name, done):
        with PickleStore(self.file_path) as store:
            store.update(date, action_name, done)
            
    def on_success(self, url, callback, resp):
        LOG(u"Repeater %s succeeded with status %s" % (url, resp.code))
        callback(resp.code == 200)
        
    def on_failure(self, url, callback, err):
        EXCEPTION(u"Repeater %s failed %s" % (url, err))
        callback(False)
    
    def __call__(self):
        DEBUG(u"Repeater starting")
        i = 0
        try:
            for url, callback in self.pending():
                DEBUG(u"Will call action %s" % (url, ))
                deferred = self.client.request(
                    'GET',
                    url,
                    Headers(self.headers)
                )
                deferred.addCallbacks(
                    partial(self.on_success, url, callback),
                    partial(self.on_failure, url, callback)
                )
                i += 1
        except:
            EXCEPTION(u"Repeater could not start")
        DEBUG(u"Repeater started %s jobs" % (i, ))  

def online_action(func):
    @wraps(func)
    def action(self, *args, **kwargs):
        assert hasattr(self, '_storage')
        return func(self, *args, **kwargs)
    return action

class PickleStore(object):
    
    def __init__(self, file_path):
        self.file_path = file_path
        
    def __enter__(self):
        if not os.path.exists(self.file_path):
            self._storage = {}
            self._storage['__from__'] = datetime.date.today()
            DEBUG(u'Initialized empty pickle store instead of %s' % (self.file_path, ))
        else: 
            DEBUG(u'Will load pickle store %s' % (self.file_path, ))
            with open(self.file_path, 'rb') as store_file:
                self._storage = load(store_file)
                DEBUG(u'Loaded pickle store %s' % (self.file_path, ))
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            DEBUG(u"Will dump pickle store %s" % (self.file_path, ))
            with open(self.file_path, 'wb') as store_file:
                dump(self._storage, store_file)
            DEBUG(u"Dumped pickle store %s" % (self.file_path, ))
        finally:
            del self._storage
            
    @online_action    
    def get_pending(self, today, action_names):
        """
        returns a generator over tuples
        (date, action_name)
        of actions that failed to work before today
        """
        store = self._storage
        first_date = store['__from__']
        for date in dates_between(first_date, today):
            for action_name in action_names:
                if action_name not in store:
                    DEBUG(u"Creating filling for new action %s" % (action_name, ))
                    store[action_name] = {}
                    yesterday = today - datetime.timedelta(days=1)
                    for fill_date in dates_between(first_date, yesterday):
                        DEBUG(u"Creating fill for new action %s on date %s" % (action_name, fill_date))
                        store[action_name][fill_date] = {'done': True, 'created': datetime.datetime.now(), 'times': []}
                action_store = store[action_name]
                if date not in action_store:
                    DEBUG(u"Creating a skipped action %s on %s" % (action_name, date))
                    action_store[date] = {'done': False, 'created': datetime.datetime.now(), 'times': []}
                    yield date, action_name
                else:
                    entry = action_store[date]
                    if entry['done']:
                        continue
                    else:
                        DEBUG(u'Found failed action %s on %s' % (action_name, date))
                        yield date, action_name
    
    @online_action                    
    def update(self, date, action_name, result):
        DEBUG(u"Updating action %s on %s status to %s" % (action_name, date, result))
        store = self._storage
        entry = store[action_name][date]
        entry['done'] = result
        entry['times'].append(datetime.datetime.now())