# coding: utf-8
import json
import re
from dateutil.parser import parse

from intranet3.helpers import Converter, serialize_url
from intranet3.log import INFO_LOG, EXCEPTION_LOG

from .base import BaseFetcher, BasicAuthMixin, FetcherBadDataError
from .bug import BaseBugProducer, BaseScrumProducer
from .request import RPC

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)


class GithubScrumProducer(BaseScrumProducer):
    def get_points(self, bug, tracker, login_mapping, parsed_data):
        digit_labels = [ int(label) for label in bug.labels if label.isdigit()]
        return digit_labels[0] if digit_labels else 0

class GithubBugProducer(BaseBugProducer):
    SCRUM_PRODUCER_CLASS = GithubScrumProducer
    def parse(self, tracker, login_mapping, raw_data):
        d = raw_data
        result = dict(
            id=str(d['number']),
            github_id=d['id'],
            desc=d['title'],
            reporter=d['user']['login'],
            owner=d['assignee']['login'] if d['assignee'] else None,
            status=d['state'],
            url=d['html_url'],
            opendate=parse(d.get('created_at', '')),
            changeddate=parse(d.get('updated_at', '')),
            labels=[label['name'] for label in d['labels']],
        )
        return result

    def get_project_name(self, tracker, login_mapping, parsed_data):
        m = re.match('(.*?)github.com/(.*?)/(.*?)($|/.*)', parsed_data['url'])
        return m and m.group(2) or ''

    def get_component_name(self, tracker, login_mapping, parsed_data):
        m = re.match('(.*?)github.com/(.*?)/(.*?)($|/.*)', parsed_data['url'])
        return m and m.group(3) or ''


class GithubFetcher(BasicAuthMixin, BaseFetcher):
    BUG_PRODUCER_CLASS = GithubBugProducer

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

    def fetch_bugs_for_query(self, ticket_ids=None, project_selector=None,
                             component_selector=None, version=None,
                             resolved=False):
        if resolved:
            return
        super(GithubFetcher, self).fetch_bugs_for_query(
            ticket_ids,
            project_selector,
            component_selector,
            version,
            resolved,
        )

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
