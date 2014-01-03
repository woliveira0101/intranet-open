# coding: utf-8
import json
import re
from functools import partial
from dateutil.parser import parse
import requests

from intranet3 import memcache
from intranet3.helpers import Converter, serialize_url
from intranet3.log import INFO_LOG, EXCEPTION_LOG

from .base import BaseFetcher, BasicAuthMixin, FetcherBadDataError
from .bug import Bug
from .request import RPC

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)


class GithubBug(Bug):

    SCRUM_LABELS = ['to verify', 'in process']

    def __init__(self, *args, **kwargs):
        self._project_name = None
        self._component_name = None
        self._severity = None
        self.url = None

        if 'url' in kwargs:
            self.url = kwargs['url']
            del kwargs['url']
        super(GithubBug, self).__init__(*args, **kwargs)

        label_names = [label['name'] for label in self.labels]
        self.scrum_labels = [label for label in label_names if label in self.SCRUM_LABELS]

        # label with number will be scrum points
        digit_labels = [ label for label in label_names if label.isdigit()]

        if digit_labels:
            self.whiteboard = dict(p=int(digit_labels[0]))

    def get_url(self):
        return self.url

    @property
    def severity(self):
        return self._severity

    @severity.setter
    def severity(self, value):
        labels = [l.get('name') for l in value]
        if u"enhancement" in labels:
            self._severity = 'enhancement'
        else:
            self._severity = ''

    @property
    def project_name(self):
        return self._project_name

    @project_name.setter
    def project_name(self, value):
        m = re.match('(.*?)github.com/(.*?)/(.*?)($|/.*)', value)
        if m:
            self._project_name = m.group(2)
        else:
            self._project_name = value

    @property
    def component_name(self):
        return self._component_name

    @component_name.setter
    def component_name(self, value):
        m = re.match('(.*?)github.com/(.*?)/(.*?)($|/.*)', value)
        if m:
            self._component_name = m.group(3)
        else:
            self._component_name = value

    def get_status(self):
        if self.status == 'closed':
            return 'CLOSED'
        else:
            try:
                label = self.scrum_labels[0]
                if label == 'to verify':
                    return 'RESOLVED'
            except IndexError:
                return 'NEW'

    def is_unassigned(self):
        try:
            label = self.scrum_labels[0]
            if label == 'in process':
                return False
            else:
                return True
        except IndexError:
            return True

github_converter = Converter(
    id='number',
    number='id',
    desc='title',
    reporter=lambda d: d['user']['login'],
    owner=lambda d:  d['assignee']['login'] if d['assignee'] else '',
    priority=lambda d: '',
    severity=lambda d: d['labels'],
    status=lambda d: d['state'],
    resolution=lambda d: 'none',
    project_name=lambda d: d['html_url'],
    component_name=lambda d: d['html_url'],
    url=lambda d: d['html_url'],
    deadline=lambda d: d['milestone']['due_on'] if d['milestone'] is not None else '',
    opendate=lambda d: parse(d.get('created_at', '')),
    changeddate=lambda d: parse(d.get('updated_at', '')),
    dependson=lambda d: {},
    blocked=lambda d: {},
    labels=lambda d: d['labels']
)


class GithubFetcher(BasicAuthMixin, BaseFetcher):
    bug_class = GithubBug
    get_converter = lambda self: github_converter

    MILESTONES_KEY = 'milestones_map' #klucz do mapowania nazwa_milestonea -> numer milestonea
    MILESTONES_TIMEOUT = 60*3

    def __init__(self, *args, **kwargs):
        super(GithubFetcher, self).__init__(*args, **kwargs)

    def fetch_milestones(self, url):
        url = str(url)
        rpc = self.get_rpc()
        rpc._args = ['GET', url]
        rpc.start()
        response = rpc.get_result()
        return self.parse_milestones(response.content)

    def parse_milestones(self, data):
        milestone_map = {}
        json_data = json.loads(data)
        for milestone in json_data:
            milestone_map[milestone['title']] = str(milestone['number'])

        return milestone_map

    def fetch_scrum(self, sprint_name, project_id=None, component_id=None):
        base_url = '%srepos/%s/%s/' % (self.tracker.url, project_id, component_id)
        milestones_url = ''.join((base_url, 'milestones'))
        issues_url = ''.join((base_url, 'issues?'))

        milestones = self.fetch_milestones(
            milestones_url,
        )

        if sprint_name not in milestones:
            raise FetcherBadDataError('There is no %s milestone' % sprint_name)

        opened_bugs_url = serialize_url(
            issues_url,
            **dict(
                milestone=milestones.get(sprint_name),
                state='open'
            )
        )

        closed_bugs_url = serialize_url(
            issues_url,
            **dict(
                milestone=milestones.get(sprint_name),
                state='closed'
            )
        )

        self.consume(RPC('GET', opened_bugs_url))
        self.consume(RPC('GET', closed_bugs_url))

    @staticmethod
    def common_url_params():
        return dict(
            state='open',
            format='json'
        )

    @staticmethod
    def single_user_params():
        return dict(
            filter='assigned'
        )

    @staticmethod
    def all_users_params():
        return dict(
            filter='all'
        )

    def fetch_user_tickets(self, resolved=False):
        if resolved:
            return
        params = self.common_url_params()
        params.update(self.single_user_params())
        url = serialize_url(self.tracker.url + 'issues?', **params)

        self.consume(RPC(
            'GET',
            url
        ))

    def fetch_all_tickets(self, resolved=False):
        if resolved:
            return
        params = self.common_url_params()
        params.update(self.all_users_params())
        url = serialize_url(self.tracker.url + 'issues?', **params)

        self.consume(RPC(
            'GET',
            url
        ))

    def fetch_bugs_for_query(self, ticket_ids, project_selector, component_selector, version, resolved=False):
        if resolved:
            return

        params = self.common_url_params()
        if ticket_ids:
            self._wanted_ticket_ids = ticket_ids

        if project_selector and component_selector:
            uri = self.tracker.url + "repos/%s/%s/issues?" % (project_selector, component_selector[0])
            url = serialize_url(uri, **params)

            self.consume(RPC(
                'GET',
                url,
            ))

    def parse(self, data):
        json_data = json.loads(data)
        return json_data
