import json

import requests
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError
import dateutil.parser

from intranet3.helpers import serialize_url, make_path
from intranet3.log import EXCEPTION_LOG, INFO_LOG

from .base import BaseFetcher, FetcherBadDataError
from .bug import BaseBugProducer
from .request import RPC

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)

ISSUE_STATE_RESOLVED = ['finished']
ISSUE_STATE_UNRESOLVED = ['started', 'unstarted', 'unscheduled', 'accepted']


class PivotalTrackerBugProducer(BaseBugProducer):

    def parse(self, tracker, login_mapping, raw_data):
        raw_data.update(dict(
            opendate=dateutil.parser.parse(raw_data['opendate']),
            changeddate=dateutil.parser.parse(raw_data['changeddate']),
            ))
        return raw_data


class PivotalTrackerTokenFetcher(BaseFetcher):
    TOKEN_MEMCACHE_KEY = '{tracker_type}-{tracker_id}-{user_id}-pivotal_token'
    TOKEN_MEMCACHE_TIMEOUT = 60*60*24

    TOKEN_URL = 'https://www.pivotaltracker.com/services/v3/tokens/active'
    BUG_PRODUCER_CLASS = PivotalTrackerBugProducer

    def __init__(self, tracker, credentials, user, login_mapping):
        super(PivotalTrackerTokenFetcher, self).__init__(
            tracker,
            credentials,
            user,
            login_mapping,
        )
        self.email = credentials['email']

    def get_auth(self):
        response = requests.get(
            self.TOKEN_URL,
            auth=HTTPBasicAuth(self.email, self.password),
            verify=False,
        )
        try:
            data = ET.fromstring(response.content)
            token = data.find('guid').text
        except ParseError:
            raise FetcherBadDataError(
                'Authentication error on tracker %s, check login and password.'
                % self.tracker.name,
            )
        return token

    def set_auth(self, session, data=None):
        token = data
        session.headers['X-TrackerToken'] = token


class PivotalTrackerFetcher(PivotalTrackerTokenFetcher):
    api_url = 'services/v5/projects'
    default_fields = 'owned_by,requested_by,estimate,:default'

    def __init__(self, *args, **kwargs):
        super(PivotalTrackerFetcher, self).__init__(*args, **kwargs)
        self._project_ids = None

    def get_project_ids(self):
        rpc = self.get_rpc()
        rpc.url = self.prepare_url()
        rpc.start()
        response = rpc.get_result()
        return self.parse_project(response.content)

    def prepare_url(self, project_id='', endpoint='', params={}):
        tracker_url = self.tracker.url.replace('http://', 'https://')
        url = make_path(tracker_url, self.api_url, project_id, endpoint)
        if params:
            url += '?'
            url = serialize_url(url, **params)
        return url

    def _get_filters(
            self, owners=None, ids=None, label=None,
            states=None, include_done=False):
        filter_params = []
        if owners:
            owners = ' or '.join(
                ['owner:"%s"' % x for x in owners]
            )
            owners = '(%s)' % owners
            filter_params.append(owners)
        if states:
            states = ','.join(states)
            states = 'state:%s' % states
            filter_params.append(states)
        if label:
            filter_params.append('label:"%s" ' % label)
        url_and = ' and '.join(filter_params)

        filter_params = []
        if ids:
            filter_params.append('id:%s ' % ','.join([str(i) for i in ids]))
        if include_done:
            filter_params.append('includedone:true')
        url_space = ' '.join(filter_params)

        url = '%s %s' % (url_and, url_space)
        return url

    def fetch(self, endpoint, params={}):
        rpcs = []
        project_ids = self.get_project_ids()
        for project_id in project_ids:
            url = self.prepare_url(project_id, endpoint, params)
            rpcs.append(RPC(url=url))
        return rpcs

    def parse_project(self, data):
        project_json = json.loads(data)
        return [p['id'] for p in project_json]

    def fetch_user_tickets(self, resolved=False):
        if resolved:
            states = ISSUE_STATE_RESOLVED
        else:
            states = ISSUE_STATE_UNRESOLVED

        params = {
            'fields': self.default_fields,
            'filter': self._get_filters(
                owners=[self.login],
                states=states,
            )
        }

        rpcs = self.fetch('stories', params=params)
        self.consume(rpcs)

    def fetch_all_tickets(self, resolved=False):
        if resolved:
            states = ISSUE_STATE_RESOLVED
        else:
            states = ISSUE_STATE_UNRESOLVED

        params = {
            'fields': self.default_fields,
            'filter': self._get_filters(
                owners=self.login_mapping.keys(),
                states=states,
                include_done=True,
            )
        }
        rpcs = self.fetch('stories', params=params)
        return self.consume(rpcs)

    def fetch_bugs_for_query(self, ticket_ids=None, project_selector=None,
                             component_selector=None, version=None,
                             resolved=False):
        super(PivotalTrackerFetcher, self).fetch_bugs_for_query(
            ticket_ids,
            project_selector,
            component_selector,
            version,
            resolved,
        )
        params = {
            'fields': self.default_fields,
            'filter': self._get_filters(
                owners=self.login_mapping.keys(),
                ids=ticket_ids,
                include_done=True,
            )
        }
        if resolved:
            params['filters']['states'] = ISSUE_STATE_RESOLVED

        rpcs = self.fetch('stories', params=params)
        self.consume(rpcs)

    def fetch_scrum(self, sprint_name, project_id=None, component_id=None):
        params = {
            'fields': self.default_fields,
            'filter': self._get_filters(
                label=sprint_name,
                include_done=True,
            )
        }
        rpcs = self.fetch('stories', params=params)
        self.consume(rpcs)

    def parse(self, data):
        stories = json.loads(data)

        result = []
        for story in stories:
            points = story.get('estimate')
            project_name = str(story['project_id'])

            owner = None
            owned_by = story.get('owned_by')
            if owned_by:
                owner = owned_by.get('name')

            labels = [l['name'] for l in story['labels']]

            bug_desc = dict(
                id=story['id'],
                desc=story['name'],
                reporter=story['requested_by']['name'],
                owner=owner,
                status=story['current_state'],
                project_name=project_name,
                opendate=story['created_at'],
                changeddate=story['updated_at'],
                points=points,
                labels=labels,
                url=story['url'],
            )
            result.append(bug_desc)
        return result
