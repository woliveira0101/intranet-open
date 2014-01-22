import urllib

import requests

from .bugzilla import BugzillaFetcher
from intranet3.log import INFO_LOG, DEBUG_LOG


LOG = INFO_LOG(__name__)
DEBUG = DEBUG_LOG(__name__)

class IgozillaFetcher(BugzillaFetcher):
    
    encoding = 'utf-8'
    delimiter=','

    def get_auth(self):
        form_fields = {
            'Bugzilla_login': self.login.encode('utf-8'),
            'Bugzilla_password': self.password.encode('utf-8')
        }
        form_data = urllib.urlencode(form_fields)
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        response = requests.post(
            self.tracker.url.encode('utf-8') + '/query.cgi',
            form_data,
            headers=headers,
        )
        return response.cookies

    def set_auth(self, session, data=None):
        cookies = data or self._auth_data
        session.cookies.update(cookies)
