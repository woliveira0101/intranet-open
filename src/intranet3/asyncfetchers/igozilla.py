import re
import urllib

import requests
from dateutil.parser import parse
from xml.etree import ElementTree as ET

from .bugzilla import BugzillaFetcher
from intranet3.log import INFO_LOG, DEBUG_LOG
from intranet3.helpers import Converter

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
        cookies = data
        session.cookies.update(cookies)
