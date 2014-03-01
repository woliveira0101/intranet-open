import json

from dateutil.parser import parse as dateparse

from intranet3.asyncfetchers.base import (
    BaseFetcher,
    BasicAuthMixin,
    FetcherBadDataError,
    FetchException,
)
from intranet3.asyncfetchers.bug import (
    BaseBugProducer,
    ToDictMixin,
)
from intranet3.asyncfetchers.request import RPC
from intranet3.log import ERROR_LOG, INFO_LOG
from intranet3.models import User

LOG = INFO_LOG(__name__)
ERROR = ERROR_LOG(__name__)


class BlockedOrDependson(ToDictMixin):
    def __init__(self, key, bug_id, status, description, tracker):
        self.id = bug_id
        self.status = status
        self.desc = description
        self.resolved = self.status in ('Closed', 'Resolved')
        self.url = tracker.url + '/browse/{}'.format(key)
        self.owner = User(name='unknown')


class JiraBugProducer(BaseBugProducer):
    def parse(self, tracker, login_mapping, raw_data):
        d = raw_data

        fields = d['fields']

        assignee = fields['assignee']
        priority = fields['priority']['name']

        return dict(
            key=d['key'],
            id=d['id'],
            desc=fields['summary'],
            reporter=fields['reporter']['name'],
            owner=assignee['name'] if assignee else '',
            priority=priority,
            severity=priority,
            status=fields['status']['name'],
            resolution=fields['resolution'],
            project_name=fields['project']['name'],
            component_name=self._get_component_name(fields),
            deadline=self._parse_date(fields['duedate']),
            opendate=self._parse_date(fields['created']),
            changeddate=self._parse_date(fields['updated']),
            labels=fields['labels'],
            dependson=self._get_depends_on(fields, tracker),
            blocked=self._get_blocked(fields, tracker),
        )

    def _get_component_name(self, fields):
        return ', '.join([c['name'] for c in fields['components']])

    def _parse_link(self, dep, tracker):
        fields = dep['fields']
        return BlockedOrDependson(
            key=dep['key'],
            bug_id=dep['id'],
            status=fields['status']['name'],
            description=fields['summary'],
            tracker=tracker,
        )

    def _parse_date(self, date_to_parse):
        return dateparse(date_to_parse) if date_to_parse else ''

    def _get_depends_on(self, fields, tracker):
        return [self._parse_link(link, tracker) for link in fields['subtasks']]

    def _get_blocked(self, dep, tracker):
        links = [
            link['outwardIssue'] for link in dep['issuelinks']
            if link['type']['name'] == 'Blocks' and 'outwardIssue' in link
        ]
        return [self._parse_link(link, tracker) for link in links]

    def get_url(self, tracker, login_mapping, parsed_data):
        key = parsed_data['key']
        return self.tracker.url + '/browse/{}'.format(key)

    def get_status(self, tracker, login_mapping, parsed_data):
        return parsed_data['status'].upper()


class JiraQueryBuilder(object):
    def __init__(self, fields=[]):
        self._jql_params = []
        self._fields = fields

    def _add_oper(self, field, data, oper):
        self._jql_params.append('"{}"{}"{}"'.format(field, oper, data))

    def eq(self, field, data):
        self._add_oper(field, data, '=')

    def neq(self, field, data):
        self._add_oper(field, data, '!=')

    def in_(self, field, data):
        params = []
        for item in data:
            params.append('"{}"="{}"'.format(field, item))
        self._jql_params.append('(' + '+OR+'.join(params) + ')')

    def get_url(self, tracker_url):
        jql = '+AND+'.join(self._jql_params)
        return '%(url)s/rest/api/2/search?jql=%(jql)s&fields=%(fields)s' % \
            {'url': tracker_url,
             'jql': jql,
             'fields': self._fields}


class JiraFetcher(BasicAuthMixin, BaseFetcher):
    """
    Fetcher for Jira bugs
    Issues statuses must follow jira classic workflow scheme
    """

    BUG_PRODUCER_CLASS = JiraBugProducer

    FIELDS = ['summary', 'reporter', 'assignee', 'priority', 'status',
              'resolution', 'project', 'components', 'duedate', 'created',
              'updated', 'labels', 'subtasks', 'issuelinks']

    def fetch(self, url):
        return RPC(url=url)

    def check_if_failed(self, response):
        if response.status_code == 401:
            login_reason = response.headers['x-seraph-loginreason']
            if 'AUTHENTICATED_FAILED' in login_reason:
                raise FetcherBadDataError(
                    "You don't have proper credentials for tracker {}"
                    .format(self.tracker.name))
        super(JiraFetcher, self).check_if_failed(response)

    def get_fields_list(self):
        return ','.join(self.FIELDS)

    def query(
        self,
        resolved=None,
        assignee=None,
        component_id=None,
        version=None,
        ticket_ids=None,
        project_id=None,
        label=None,
    ):
        query = JiraQueryBuilder(self.get_fields_list())

        if resolved is not None:
            if resolved:
                query.in_('status', ['resolved', 'closed'])
            else:
                query.in_('status', ['open', 'reopened', 'in progress'])

        if assignee:
            query.eq('assignee', assignee)

        if project_id:
            query.eq('project', project_id)

        if component_id:
            query.in_('component', component_id)

        if version:
            query.in_('affectedVersion', version)

        if ticket_ids:
            query.in_('id', ticket_ids)

        if label:
            query.eq('labels', label)

        return query.get_url(self.tracker.url)

    def parse(self, data):
        try:
            data = json.loads(data)
        except ValueError as e:
            ERROR('Error while parsing jira response:\n%s' % e)
            raise FetchException(e)

        return data['issues']

    def fetch_user_tickets(self, resolved=False):
        url = self.query(resolved=resolved, assignee=self.login)
        rpc = self.fetch(url)
        self.consume(rpc)

    def fetch_all_tickets(self, resolved=False):
        url = self.query(resolved=resolved)
        rpc = self.fetch(url)
        self.consume(rpc)

    def fetch_bugs_for_query(self, ticket_ids=None, project_selector=None,
                             component_selector=None, version=None,
                             resolved=False):
        url = self.query(
            resolved=resolved,
            ticket_ids=ticket_ids,
            project_id=project_selector,
            component_id=component_selector,
            version=version,
        )
        rpc = self.fetch(url)
        self.consume(rpc)

    def fetch_scrum(self, sprint_name, project_id, component_id=None):
        url = self.query(
            label=sprint_name,
            project_id=project_id,
            component_id=component_id,
        )
        rpc = self.fetch(url)
        self.consume(rpc)
