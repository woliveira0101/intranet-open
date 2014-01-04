from dateutil.parser import parse

from intranet3.helpers import serialize_url
from intranet3.log import INFO_LOG, EXCEPTION_LOG

from .base import BaseFetcher, CSVParserMixin, BasicAuthMixin
from .nbug import BaseBugProducer, BaseScrumProducer
from .request import RPC

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)


class TracBugProducer(BaseBugProducer):
    def parse(self, tracker, login_mapping, raw_data):
        d = raw_data
        return dict(
            id=d['id'],
            desc=d['summary'],
            reporter=d['reporter'],
            owner=d['owner'],
            priority=d.get('priority') or d.get('severity'),
            severity=d.get('priority') or d.get('severity'),
            status=d['status'],
            project_name=d.get('client_name', 'none'),
            component_name=d['component'],
            opendate=parse(d.get('time', '')),
            changeddate=parse(d.get('changetime', '')),
        )

    def get_url(self, tracker, login_mapping, parsed_data):
        return tracker.url + '/ticket/' + parsed_data['id']


class TracFetcher(BasicAuthMixin, CSVParserMixin, BaseFetcher):
    BUG_PRODUCER_CLASS = TracBugProducer

    def fetch(self, url):
        self.consume(RPC(
            'GET',
            url,
        ))

    def common_url_params(self):
        return dict(
            max='1000',
            status=['assigned', 'new', 'reopened'],
            order='priority',
            col=[
                'id', 'summary', 'status', 'type', 'priority', 'severity',
                'milestone', 'component', 'reporter', 'owner', 'client_name',
                'time', 'changetime', 'blockedby', 'dependencies', 'blocking'
            ],
            format='csv'
        )

    def resolved_common_url_params(self):
        params = self.common_url_params()
        params.update(dict(
            resolution=['fixed'],
            status=['resolved', 'verified'],
        ))
        return params
        
    def single_user_params(self):
        return dict(
            owner=self.login
        )

    def all_users_params(self):
        return dict(
            owner=self.login_mapping.keys()
        )

    def fetch_user_tickets(self, resolved=False):
        if resolved:
            params = self.resolved_common_url_params()
        else:
            params = self.common_url_params()

        params.update(self.single_user_params())
        if resolved:
            params['reporter'] = params['owner']
            del params['owner']

        url = serialize_url(self.tracker.url + '/query?', **params)
        self.fetch(url)

    def fetch_all_tickets(self, resolved=False):
        if resolved:
            params = self.resolved_common_url_params()
        else:
            params = self.common_url_params()

        params.update(self.all_users_params())
        if resolved:
            params['reporter'] = params['owner']
            del params['owner']
        url = serialize_url(self.tracker.url + '/query?', **params)
        self.fetch(url)

    def fetch_bugs_for_query(self, ticket_ids, project_selector, component_selector, version, resolved=False):
        if resolved:
            params = self.resolved_common_url_params()
        else:
            params = self.common_url_params()

        if ticket_ids:
            params.update(id=[str(id) for id in ticket_ids])
        else:
            if project_selector:
                params.update(client_name=project_selector)
                if component_selector:
                    params.update(component=component_selector)
        url = serialize_url(self.tracker.url + '/query?', **params)
        self.fetch(url)
