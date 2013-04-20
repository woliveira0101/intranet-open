from functools import partial
from Cookie import SimpleCookie

from intranet3.asyncfetchers.trac import TracFetcher
from intranet3.asyncfetchers.base import FetchException, cached_bug_fetcher
from intranet3.log import INFO_LOG, DEBUG_LOG

LOG = INFO_LOG(__name__)
DEBUG = DEBUG_LOG(__name__)

class CookieTracFetcher(TracFetcher):
    
    def __init__(self, *args, **kwargs):
        super(CookieTracFetcher, self).__init__(*args, **kwargs)
        self.auth_token = None
   
    def get_headers(self):
        headers = super(CookieTracFetcher, self).get_headers()
        if self.auth_token:
            headers['Cookie'] = ['trac_auth=%s' % (self.auth_token, )]
        return headers

    @cached_bug_fetcher(lambda: u'user')        
    def fetch_user_tickets(self):
        """ Start fetching tickets for current user """
        self.fetch_auth_token(partial(TracFetcher.fetch_user_tickets, self))

    @cached_bug_fetcher(lambda: u'all')
    def fetch_all_tickets(self):
        """ Start fetching tickets for all users in mapping """
        self.fetch_auth_token(partial(TracFetcher.fetch_all_tickets, self))

    @cached_bug_fetcher(lambda: u'user-resolved')
    def fetch_user_resolved_tickets(self):
        self.fetch_auth_token(partial(TracFetcher.fetch_user_resolved_tickets, self))

    @cached_bug_fetcher(lambda: u'all-resolved')
    def fetch_all_resolved_tickets(self):
        self.fetch_auth_token(partial(TracFetcher.fetch_all_resolved_tickets, self))
        
    def fetch_bugs_for_query(self, ticket_ids, project_selector, component_selector, version):
        self.fetch_auth_token(partial(TracFetcher.fetch_bugs_for_query, self, ticket_ids, project_selector, component_selector, version))
        
    def fetch_resolved_bugs_for_query(self, ticket_ids, project_selector, component_selector, version):
        self.fetch_auth_token(partial(TracFetcher.fetch_resolved_bugs_for_query, self, project_selector, component_selector, version))
    
    def fetch_dependons_for_ticket_ids(self, ticket_ids):
        self.fetch_auth_token(partial(TracFetcher.fetch_dependons_for_ticket_ids, self, ticket_ids))
        
    def fetch_bug_titles_and_depends_on(self, ticket_ids):
        self.fetch_auth_token(partial(TracFetcher.fetch_bug_titles_and_depends_on, self, ticket_ids))
        
    def fetch_auth_token(self, callback):
        headers = self.get_headers()
        self.request(self.tracker.url.encode('utf-8') + '/login', headers, partial(self.on_auth_token_responded, callback))
    
    def on_auth_token_responded(self, callback, resp):
        DEBUG(u'Auth token response code %s' % (resp.code, ))
        if resp.code == 302:
            headers = resp.headers
            if headers.hasHeader('Set-Cookie'):
                header = resp.headers.getRawHeaders('Set-Cookie')
                if header:
                    header = '; '.join(header)
                cookie = SimpleCookie(header)
                token = cookie.get('trac_auth')
                if not token:
                    self.fail(ValueError(u'Auth token not found'))
                else:
                    self.auth_token = token.value
                    DEBUG(u'Issuing on_auth_token_responded callback')
                    callback()
            else:
                self.fail(ValueError(u'No cookie found'))
        else:
            self.fail(FetchException(u'Received response %s' % (resp.code, )))
