import re
import urllib
from functools import partial
from dateutil.parser import parse
from xml.etree import ElementTree as ET

from Cookie import SimpleCookie

from intranet3.asyncfetchers.bugzilla import BugzillaFetcher, FetchException
from intranet3.log import INFO_LOG, DEBUG_LOG
from intranet3.helpers import Converter
from intranet3.asyncfetchers.base import cached_bug_fetcher

LOG = INFO_LOG(__name__)
DEBUG = DEBUG_LOG(__name__)

igozilla_converter = Converter(
    id='bug_id',
    desc='short_desc',
    reporter='reporter',
    owner='assigned_to',
    priority='priority',
    severity='bug_severity',
    status='bug_status',
    resolution='resolution',
    project_name='product',
    component_name='component',
    deadline='deadline',
    opendate=lambda d: parse(d.get('opendate', '')),
    changeddate=lambda d: parse(d.get('changeddate', '')),
    whiteboard='status_whiteboard',
    version='version',
)

class IgozillaFetcher(BugzillaFetcher):
    
    encoding = 'utf-8'
    
    get_converter = lambda self: igozilla_converter
    
    delimiter=','
    
    def __init__(self, *args, **kwargs):
        super(IgozillaFetcher, self).__init__(*args, **kwargs)
        self.auth_login = None
        self.auth_token = None
    
    def fetch_auth_token(self, callback):
        form_fields = {
            'Bugzilla_login': self.login.encode('utf-8'),
            'Bugzilla_password': self.password.encode('utf-8')
        }
        form_data = urllib.urlencode(form_fields)
        headers = self.get_headers()
        headers['Content-Type'] = ['application/x-www-form-urlencoded']
        self.request(
            self.tracker.url.encode('utf-8') + '/query.cgi',
            headers,
            partial(self.on_auth_token_responded, callback),
            self.failed,
            'POST',
            form_data
        )
    
    def get_headers(self):
        headers = super(IgozillaFetcher, self).get_headers()
        if self.auth_login and self.auth_token:
            del headers['Authorization'] # BasicHTTP auth not needed
            headers['Cookie'][0] += '; Bugzilla_login=%s; Bugzilla_logincookie=%s' % (self.auth_login, self.auth_token)
        return headers

    def fetch_scrum(self, sprint_name, project_id=None, component_id=None):
        self.fetch_auth_token(partial(BugzillaFetcher.fetch_scrum, self, sprint_name, project_id))

    @cached_bug_fetcher(lambda: u'user')
    def fetch_user_tickets(self):
        """ Start fetching tickets for current user """
        self.fetch_auth_token(partial(BugzillaFetcher.fetch_user_tickets, self))
    
    @cached_bug_fetcher(lambda: u'all')
    def fetch_all_tickets(self):
        """ Start fetching tickets for all users in mapping """
        self.fetch_auth_token(partial(BugzillaFetcher.fetch_all_tickets, self))
    
    @cached_bug_fetcher(lambda: u'user-resolved')    
    def fetch_user_resolved_tickets(self):
        """ Start fetching tickets for current user """
        self.fetch_auth_token(partial(BugzillaFetcher.fetch_user_resolved_tickets, self))
    
    @cached_bug_fetcher(lambda: u'all-resolved')
    def fetch_all_resolved_tickets(self):
        """ Start fetching tickets for all users in mapping """
        self.fetch_auth_token(partial(BugzillaFetcher.fetch_all_resolved_tickets, self))
        
    def fetch_bugs_for_query(self, ticket_ids, project_selector, component_selector, version):
        self.fetch_auth_token(partial(BugzillaFetcher.fetch_bugs_for_query, self, ticket_ids, project_selector, component_selector, version))
        
    def fetch_resolved_bugs_for_query(self, ticket_ids, project_selector, component_selector, version):
        self.fetch_auth_token(partial(BugzillaFetcher.fetch_resolved_bugs_for_query, self, project_selector, component_selector, version))
    
    def fetch_dependons_for_ticket_ids(self, ticket_ids):
        self.fetch_auth_token(partial(BugzillaFetcher.fetch_dependons_for_ticket_ids, self, ticket_ids))
        
    def fetch_bug_titles_and_depends_on(self, ticket_ids):
        self.fetch_auth_token(partial(BugzillaFetcher.fetch_bug_titles_and_depends_on, self, ticket_ids))
    
    def on_auth_token_responded(self, callback, resp):
        DEBUG(u'Auth token response code %s' % (resp.code, ))
        if resp.code == 200:
            headers = resp.headers
            if headers.hasHeader('Set-Cookie'):
                header = resp.headers.getRawHeaders('Set-Cookie')
                if header:
                    header = '; '.join(header)
                cookie = SimpleCookie(header)
                login = cookie.get('Bugzilla_login')
                token = cookie.get('Bugzilla_logincookie')
                if not token or not login:
                    self.fail(ValueError(u'Auth token not found'))
                else:
                    self.auth_login = login.value
                    self.auth_token = token.value
                    DEBUG(u'Issuing on_auth_token_responded callback')
                    callback()
            else:
                self.fail(ValueError(u'No cookie found'))
        else:
            self.fail(FetchException(u'Received response %s' % (resp.code, )))

    def parse_dependson_and_blocked_bugs_xml(self, data):
        try:
            data = re.sub(r'<\?xml[^\?]*\?>', '<?xml version="1.0" encoding="iso-8859-2"?>', data)
            xml = ET.fromstring(data)
            self.update_bugs_statuses(xml)
        except BaseException, e:
            self.failed(e)
        else:
            self.update_depensons_and_blocked_status()
            self.success()
        