from intranet3.models.project import SelectorMapping
from intranet3 import helpers as h
from .request import RPC
from .nbase import BaseFetcher, BasicAuthMixin, CSVParserMixin, Bug


class BugzillaBug(Bug):
    def get_owner(self, data):
        return data['assigned_to']

    def get_reporter(self, data):
        return data['reporter']

    @property
    def id(self):
        return self.data['bug_id']

    @property
    def desc(self):
        return self.data['short_desc']

    @property
    def priority(self):
        return self.data['priority']

    @property
    def severity(self):
        return self.data['bug_severity']

    @property
    def status(self):
        return self.data['bug_status']

    @property
    def resolution(self):
        return self.data['resolution']

    @property
    def url(self):
        self.tracker.get_bug_url(self.id)

    @property
    def project_id(self):
        project_id = SelectorMapping(self.tracker).match(
            self.id,
            self.data['product'],
            self.data['component'],
            self.data['version'],
        )
        return project_id

    @property
    def opendate(self):
        return None

    @property
    def changeddate(self):
        return None


class BugzillaFetcher(CSVParserMixin, BasicAuthMixin, BaseFetcher):
    BUG_CLASS = BugzillaBug

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
