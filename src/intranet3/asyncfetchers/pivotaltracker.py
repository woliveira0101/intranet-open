import datetime

import requests
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET

from intranet3.helpers import Converter, serialize_url, make_path
from intranet3.log import EXCEPTION_LOG, INFO_LOG

from .base import BaseFetcher
from .nbug import BaseBugProducer, BaseScrumProducer
from .request import RPC

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)

ISSUE_STATE_RESOLVED = ['finished']
ISSUE_STATE_UNRESOLVED = ['started','unstarted','unscheduled', 'accepted']


class PivotalTrackerBugProducer(BaseBugProducer):

    def parse(self, tracker, login_mapping, raw_data):
        d = raw_data
        return dict(
            id=d['id'],
            desc=d['desc'],
            reporter=d['reporter'],
            owner=d['owner'],
            status=d['status'],
            project_name=d['project_name'],
            opendate=datetime.datetime.strptime(d['opendate'],'%Y/%m/%d %H:%M:%S %Z'),
            changeddate=datetime.datetime.strptime(d['changeddate'],'%Y/%m/%d %H:%M:%S %Z'),
            points=d['points'],
        )

    def get_status(self, tracker, login_mapping, parsed_data):
        status = parsed_data['status']
        if status == 'delivered':
            return 'CLOSED'
        elif status in ISSUE_STATE_RESOLVED:
            return 'RESOLVED'
        elif status in ISSUE_STATE_UNRESOLVED:
            return 'NEW'
        return 'NEW'

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
        try:
            email, login =  credentials.login.split(';')
        except Exception:
            email, login = '', ''

        self.email = email
        self.login = login
        self.login_mapping = dict([
            (k.split(';')[1], v) for k, v in login_mapping.iteritems() if ';' in k
        ])

    def get_auth(self):
        response = requests.get(
            self.TOKEN_URL,
            auth=HTTPBasicAuth(self.email, self.password),
        )
        data = ET.fromstring(response.content)
        token = data.find('guid').text
        return token

    def set_auth(self, session, data=None):
        token = data
        session.headers['X-TrackerToken'] = token


class PivotalTrackerFetcher(PivotalTrackerTokenFetcher):
    api_url = 'services/v3/projects'


    def __init__(self, *args, **kwargs):
        super(PivotalTrackerFetcher, self).__init__(*args, **kwargs)
        self._project_ids = None

    def get_project_ids(self):
        rpc = self.get_rpc()
        rpc._args = ['GET', self.prepare_url()]
        rpc.start()
        response = rpc.get_result()
        return self.parse_project(response.content)

    def prepare_url(self, project_id='', endpoint='', filters={}):
        tracker_url = self.tracker.url.replace('http://', 'https://')
        url = make_path(tracker_url, self.api_url, project_id, endpoint) + '?'
        filter_param = ' '.join([ '%s:%s' % (filter_name, filter) for filter_name, filter in filters.iteritems()])
        full_url = serialize_url(url, filter=filter_param)
        return full_url

    def fetch(self, endpoint, filters={}):
        rpcs = []
        project_ids = self.get_project_ids()
        for project_id in project_ids:
            url = self.prepare_url(project_id, endpoint, filters)
            rpcs.append(RPC('GET', url))
        return rpcs

    def parse_project(self, data):
        xml = ET.fromstring(data)
        return [p.text for p in xml.findall('project/id')]

    def fetch_user_tickets(self, resolved=False):
        if resolved:
            state = ','.join(ISSUE_STATE_RESOLVED)
        else:
            state =','.join(ISSUE_STATE_UNRESOLVED)

        rpcs = self.fetch('stories', filters=dict(
            owner='"%s"' % self.login,
            state=state,
        ))
        self.consume(rpcs)

    def fetch_all_tickets(self, resolved=False):
        if resolved:
            state = ','.join(ISSUE_STATE_RESOLVED)
        else:
            state = ','.join(ISSUE_STATE_UNRESOLVED)

        self.fetch('stories', filters=dict(
            state=state,
        ))

    def fetch_bugs_for_query(self, ticket_ids, project_selector, component_selector, version, resolved=False):
        filters = dict(
            id=','.join(ticket_ids),
        )
        if resolved:
            filters['state'] = ','.join(ISSUE_STATE_UNRESOLVED)

        rpcs = self.fetch('stories', filters=filters)
        self.consume(rpcs)

    def fetch_scrum(self, sprint_name, project_id=None, component_id=None):
        rpcs = self.fetch('stories', filters=dict(
            label=sprint_name,
            includedone='true',
        ))
        self.consume(rpcs)

    def parse(self, data):
        xml = ET.fromstring(data)

        result = []
        for story in xml.findall('story'):
            owner_name_node = story.find('owned_by')

            if owner_name_node is not None:
                owner_name = owner_name_node.text
            else:
                owner_name = ''

            points = story.find('estimate')
            try:
                points = points.text
            except AttributeError:
                points = 0

            if not points:
                points = 0
            points = int(points)

            bug_desc = dict(
                tracker=self.tracker,
                id=story.find('id').text,
                desc=story.find('name').text,
                reporter=story.find('requested_by').text,
                owner=owner_name,
                status=story.find('current_state').text,
                project_name=story.find('project_id').text,
                opendate=story.find('created_at').text,
                changeddate=story.find('updated_at').text,
                points=points,
            )
            result.append(bug_desc)
        return result
