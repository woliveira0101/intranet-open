import csv
from dateutil.parser import parse
from functools import partial

from intranet3.helpers import Converter, serialize_url
from intranet3.log import INFO_LOG, EXCEPTION_LOG
from intranet3.helpers import decoded_dict

from .base import BaseFetcher, CSVParserMixin, BasicAuthMixin
from .bug import Bug
from .request import RPC

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)

class TracBug(Bug):
    
    def get_url(self, number=None):
        number = number if number else self.id
        return self.tracker.url + '/ticket/' + number


def get_depends_on(bug_desc):
    if 'blockedby' in bug_desc:
        deps = bug_desc['blockedby']
    elif 'dependencies' in bug_desc:
        deps = bug_desc['dependencies']
    else:
        return []
    output = []
    for dep in deps.split(', '):
        try:
            id = int(dep)
        except ValueError: # nl trac can return '--'
            continue
        else:
            output.append(str(id))
    return output


trac_converter = Converter(
    id='id',
    desc='summary',
    reporter='reporter',
    owner='owner',
    priority=lambda d: d.get('priority') or d.get('severity'),
    severity=lambda d: d.get('priority') or d.get('severity'),
    status='status',
    resolution=lambda d: '',
    project_name=lambda d: d.get('client_name', 'none'),
    component_name='component',
    deadline='deadline',
    opendate=lambda d: parse(d.get('time', '')),
    changeddate=lambda d: parse(d.get('changetime', '')),
    dependson=lambda d: dict((bug, {'resolved': False}) for bug in get_depends_on(d) if bug),
    blocked=lambda d: dict((bug, {'resolved': False}) for bug in d.get('blocking', '').split(', ') if bug)
)

class TracFetcher(BasicAuthMixin, CSVParserMixin, BaseFetcher):
    bug_class = TracBug
    get_converter = lambda self: trac_converter
    
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
            col=['id', 'summary', 'status', 'type', 'priority', 'severity', 'milestone', 'component', 'reporter', 'owner', 'client_name', 'time', 'changetime', 'blockedby', 'dependencies', 'blocking'],
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

    def fetch_user_tickets(self):
        params = self.common_url_params()
        params.update(self.single_user_params())
        url = serialize_url(self.tracker.url + '/query?', **params)
        self.fetch(url)

    def fetch_all_tickets(self):
        params = self.common_url_params()
        params.update(self.all_users_params())
        url = serialize_url(self.tracker.url + '/query?', **params)
        self.fetch(url)

    def fetch_user_resolved_bugs(self):
        params = self.resolved_common_url_params()
        params.update(self.single_user_params())
        params['reporter'] = params['owner']
        del params['owner']
        url = serialize_url(self.tracker.url + '/query?', **params)
        self.fetch(url)

    def fetch_all_resolved_bugs(self):
        params = self.resolved_common_url_params()
        params.update(self.all_users_params())
        params['reporter'] = params['owner']
        del params['owner']
        url = serialize_url(self.tracker.url + '/query?', **params)
        self.fetch(url)

    def fetch_bugs_for_query(self, ticket_ids, project_selector, component_selector, version):
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

    def fetch_resolved_bugs_for_query(self, ticket_ids, project_selector, component_selector, version):
        params = self.resolved_common_url_params()
        if ticket_ids:
            params.update(id=[str(id) for id in ticket_ids])
        else:
            if project_selector:
                params.update(client_name=project_selector)
                if component_selector:
                    params.update(component=component_selector)
        url = serialize_url(self.tracker.url + '/query?', **params)
        self.fetch(url)
