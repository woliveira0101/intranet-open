import json
from functools import partial
from dateutil.parser import parse
from xml.etree import ElementTree as ET

from pyramid.decorator import reify

from intranet3.asyncfetchers.base import ( BaseFetcher, CSVParserMixin,
    SimpleProtocol, BasicAuthMixin,
    FetchException, Bug, cached_bug_fetcher )
from intranet3 import helpers as h
from intranet3.log import EXCEPTION_LOG, INFO_LOG


LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)


class JiraBug(Bug):

    def get_url(self, number=None):
        number = number if number else self.id
        # return self.tracker.url + '/browse/%(id)s' % {'id': number}
        return self.tracker.url + '/ViewIssue.jspa?id=%(id)s' % {'id': number}

    def is_unassigned(self):
        return not self.owner

    @reify
    def is_blocked(self):
        for bug_data in self.dependson.values():
            if bug_data.get('resolved', True) is False:
                return True
        return False

    def get_status(self):
        return self.status

    def get_resolution(self):
        return self.resolution


def _fetcher_function(resolved, single):
    @cached_bug_fetcher(lambda: u'resolved-%s-single-%s' % (resolved, single))
    def fetcher(self):
        jql_params = []
        if resolved:
            jql_params.append('status=done')
        else:
            jql_params.append('status!=done')
        if single:
            jql_params.append('assignee=' + self.login)
        jql = '+AND+'.join(jql_params)
        url = '%(url)s/rest/api/2/search?jql=%(jql)s' % \
            {'url': self.tracker.url, 'jql': jql }
        self.fetch_get(url)
    return fetcher

def _query_fetcher_function(resolved=False, all=False):
    def fetcher(self, ticket_ids, project_selector, component_selector,
                version):
        jql_params = ['project=' + project_selector]
        if component_selector:
            jql_params.append(build_query_alternative('component', component_selector))
        if version:
            jql_params.append(build_query_alternative('affectedVersion', version))
        if ticket_ids:
            jql_params.append(build_query_alternative('id', ticket_ids))

        if not all:
            if resolved:
                jql_params.append('status=done')
            else:
                jql_params.append('status!=done')

        jql = '+AND+'.join(jql_params)
        url = '%(url)s/rest/api/2/search?jql=%(jql)s' % \
            {'url': self.tracker.url, 'jql': jql }
        self.fetch_get(url)
    return fetcher

def build_query_alternative(field, data):
    params = []
    for item in data:
        params.append(field + '=' + item)
    return '(' + '+OR+'.join(params) + ')'


def get_blocked(d):
    links = filter(lambda l: l['type']['id'] == '10000' and 'outwardIssue' in l, d['fields']['issuelinks'])
    links = map(lambda l: l['outwardIssue'], links)
    return dict(map(lambda t: (t['id'], {'desc': t['fields']['summary'], 'resolved': t['fields']['status']['id'] == '10000'}), links))


jira_converter = h.Converter(
    id=lambda d: d['id'],
    desc=lambda d: d['fields']['summary'],
    reporter=lambda d: d['fields']['reporter']['name'],
    owner=lambda d: d['fields']['assignee']['name'] if d['fields']['assignee'] else '',
    priority=lambda d: d['fields']['priority']['name'],
    severity=lambda d: d['fields']['priority']['name'],
    status=lambda d: d['fields']['status']['name'],
    resolution=lambda d: d['fields']['resolution'],
    project_name=lambda d: d['fields']['project']['name'],
    component_name=lambda d: ', '.join(map(lambda c: c['name'], d['fields']['components'])),
    deadline=lambda d: parse(d['fields']['duedate']) if d['fields']['duedate'] else '',
    opendate=lambda d: parse(d['fields']['created']),
    changeddate=lambda d: parse(d['fields']['updated']) if d['fields']['updated'] else '',
    labels=lambda d: d['fields']['labels'],
    dependson=lambda d: dict(map(lambda t: (t['id'], {'desc': t['fields']['summary'], 'resolved': t['fields']['status']['id'] == '10000'}), d['fields']['subtasks'])),
    blocked=get_blocked
)


class JiraFetcher(BasicAuthMixin, CSVParserMixin, BaseFetcher):
    """ Fetcher for Jira bugs """

    # redirect_support = True
    bug_class = JiraBug
    get_converter = lambda self: jira_converter

    def fetch_get(self, url, on_success=None):
        if not on_success:
            on_success = self.responded
        url = url.encode('utf-8')
        headers = self.get_headers()
        self.request(url, headers, on_success, method='GET')

    def parse(self, data):
        converter = self.get_converter()
        json_data = json.loads(data)
        for bug_desc in json_data['issues']:
            yield self.bug_class(
                tracker=self.tracker,
                **converter(bug_desc)
            )

    fetch_user_tickets = _fetcher_function(resolved=False, single=True)

    fetch_all_tickets = _fetcher_function(resolved=False, single=False)

    fetch_user_resolved_tickets = _fetcher_function(resolved=True, single=True)

    fetch_all_resolved_tickets = _fetcher_function(resolved=True, single=False)

    fetch_bugs_for_query = _query_fetcher_function(resolved=False)

    fetch_resolved_bugs_for_query = _query_fetcher_function(resolved=True)

    fetch_all_bugs_for_query = _query_fetcher_function(all=True)
