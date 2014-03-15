import datetime
import httplib2

from apiclient.discovery import build
from oauth2client.client import AccessTokenCredentials
from apiclient.errors import Error

from intranet3 import config
from intranet3.log import EXCEPTION_LOG

EXCEPTION = EXCEPTION_LOG(__name__)

#shortcut, in most cases we will be using whole calendar module
oneday = datetime.timedelta(days=1)
onehour = datetime.timedelta(hours=1)


class Event(object):
    """
        Event helper class.
        3 properties (or arguments for __init__) are obligatory:
            start(inclusive), end(exclusive) - date or datetime without timezone (Europe/Warsaw is default)
            title = string
        1 property/argument is optional:
            description - description of event
    """
    _json = {}
    _start = None
    _end = None

    def __init__(self, start, end, title, description=None):
        self.start = start
        self.end = end
        self.title = title
        if description:
            self.description = description

    def _time_getter(prop):
        def func(self):
            return getattr(self, '_%s' % prop, None)
        return func

    def _time_setter(prop):
        def func(self, value):
            if isinstance(value, datetime.datetime):
                string_value = value.isoformat()
                self._json[prop] = {}
                self._json[prop]['dateTime'] = string_value
                self._json[prop]['timeZone'] = 'Europe/Warsaw'
            elif isinstance(value, datetime.date):
                string_value = value.strftime('%Y-%m-%d')
                self._json[prop] = {}
                self._json[prop]['date'] = string_value
            else:
                raise NotImplementedError('Unimplemented argument')

            setattr(self, '_%s' % prop, value)
        return func

    def _title_setter(self, title):
        self._json['summary'] = title

    def _title_getter(self):
        return self._json.get('summary')

    def _desc_setter(self, desc):
        self._json['description'] = desc

    def _desc_getter(self):
        return self._json.get('description')

    start = property(_time_getter('start'), _time_setter('start'))
    end = property(_time_getter('end'), _time_setter('end'))
    title = property(_title_getter, _title_setter)
    description = property(_desc_getter, _desc_setter)


class Calendar(object):

    def __init__(self, user):
        self._user = user
        self._name = user.email
        self._error = False

        dev_key = config['GOOGLE_DEVELOPERS_KEY']
        try:
            credentials = AccessTokenCredentials(user.access_token, 'intranet/1.0')
            http = httplib2.Http()
            http = credentials.authorize(http)
            self._service = build(
                serviceName='calendar',
                version='v3',
                http=http,
               developerKey=dev_key
            )
        except Exception as e:
            self._error = True
            EXCEPTION("Can't refresh token for user %s: %s" % (user.email, e))


    def addEvent(self, event):
        # we assume that calendarId is the same as user's email address
        if self._error:
            return None
        try:
            created_event = self._service.events().insert(calendarId=self._name, body=event._json).execute()
        except Error as e:
            EXCEPTION('Calendar: Failed to add event to calendar: %s' % e)
            return None

        return created_event['id']
