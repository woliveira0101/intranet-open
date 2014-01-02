from dateutil.parser import parse
from pyramid.decorator import reify

from intranet3 import helpers as h
from .request import RPC
from .base import BaseFetcher, BasicAuthMixin, CSVParserMixin
from .bug import Bug

bugzilla_converter = h.Converter(
    id='bug_id',
    desc='short_desc',
    reporter='reporter',
    owner='assigned_to',
    priority=lambda d: d.get('priority', ''), # + '/' + d['priority'],
    severity=lambda d: d.get('bug_severity', ''),
    status=lambda d: d.get('bug_status', ''), # + '/' + d['resolution'],
    resolution=lambda d: d.get('resolution', ''),
    project_name='product',
    component_name='component',
    deadline='deadline',
    opendate=lambda d: parse(d.get('opendate', '')),
    changeddate=lambda d: parse(d.get('changeddate', '')),
    whiteboard='status_whiteboard',
    version='version',
)

class BugzillaBug(Bug):

    def get_url(self, number=None):
        number = number if number else self.id
        return self.tracker.url + '/show_bug.cgi?id=%(id)s' % {'id': number}

    def is_unassigned(self):
        return not self.owner or not self.owner.email.endswith('stxnext.pl')

    @reify
    def is_blocked(self):
        wb_blocked = self.whiteboard.get('blocked')
        if wb_blocked in h.positive_values:
            return True

        if wb_blocked is None: # blocked param is not set
            for bug_data in self.dependson.values():
                if bug_data.get('resolved', True) is False:
                    return True

        return False

    def get_status(self):
        return self.status

    def get_resolution(self):
        return self.resolution


class BugzillaFetcher(CSVParserMixin, BasicAuthMixin, BaseFetcher):
    bug_class = BugzillaBug
    get_converter = lambda self: bugzilla_converter

    COLUMNS = (
        'bug_severity', 'assigned_to', 'version',
        'bug_status', 'resolution', 'product', 'op_sys', 'short_desc',
        'reporter', 'opendate', 'changeddate', 'component', 'deadline',
        'bug_severity', 'product', 'priority', 'status_whiteboard'
    )

    COLUMNS_COOKIE = "%20".join(COLUMNS)

    def common_url_params(self):
        return dict(
            bug_status=['NEW', 'ASSIGNED', 'REOPENED', 'UNCONFIRMED',
                        'CONFIRMED', 'WAITING'],
            ctype='csv',
            emailassigned_to1='1'
        )

    def resolved_common_url_params(self):
        return {
            'bug_status':['RESOLVED', 'VERIFIED'],
            'ctype':'csv',
            'emailreporter1':'1',
            'field0-0-0':'resolution',
            'type0-0-0':'notequals',
            'value0-0-0':'LATER'
        }

    def single_user_params(self):
        return dict(
            emailtype1='exact',
            email1=self.login
        )

    def all_users_params(self):
        return dict(
            emailtype1='regexp',
            email1='(' + '|'.join(self.login_mapping.keys()) + ')'
        )

    def add_data(self, session):
        from requests.cookies import create_cookie
        session.cookies.set_cookie(
            create_cookie('COLUMNLIST', self.COLUMNS_COOKIE)
        )

    def fetch_scrum(self, sprint_name, project_id=None, component_id=None):
        params = dict(
            ctype='csv',
            status_whiteboard_type='regexp',
            status_whiteboard=self.SPRINT_REGEX % sprint_name,
            bug_status=[
                'NEW',
                'ASSIGNED',
                'REOPENED',
                'UNCONFIRMED',
                'CONFIRMED',
                'WAITING',
                'RESOLVED',
                'VERIFIED',
                'CLOSED'
            ],
        )
        url = '%s/buglist.cgi' % self.tracker.url

        body = h.serialize_url('', **params)
        rpc = RPC('POST', url, data=body)
        self.consume(rpc)

    def fetch_user_tickets(self, resolved=False):
        params = self.resolved_common_url_params() \
            if resolved else self.common_url_params()
        params.update(self.single_user_params())

        url = '%s/buglist.cgi' % self.tracker.url
        body = h.serialize_url('', **params)
        rpc = RPC('POST', url, data=body)
        self.consume(rpc)

    def fetch_all_tickets(self, resolved=False):
        params = self.resolved_common_url_params() \
            if resolved else self.common_url_params()
        params.update(self.all_users_params())

        url = '%s/buglist.cgi' % self.tracker.url
        body = h.serialize_url('', **params)
        rpc = RPC('POST', url, data=body)
        self.consume(rpc)
