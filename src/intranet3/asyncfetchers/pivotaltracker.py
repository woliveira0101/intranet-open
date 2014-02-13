import base64
import xml.etree.ElementTree as ET
from functools import partial
import dateutil.parser
import json

from intranet3.asyncfetchers.base import BaseFetcher, Bug, cached_bug_fetcher
from intranet3.helpers import Converter, serialize_url, make_path
from intranet3.log import EXCEPTION_LOG, INFO_LOG
from intranet3 import memcache

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)

ISSUE_STATE_RESOLVED = ['finished']
ISSUE_STATE_UNRESOLVED = ['started', 'unstarted', 'unscheduled', 'accepted']


class PivotalTrackerBug(Bug):

    def get_url(self, number=None):
        number = number if number else self.id
        return make_path(self.tracker.url, '/story/show', number)

    def get_status(self):
        if self.status == 'delivered':
            return 'CLOSED'
        elif self.status in ISSUE_STATE_RESOLVED:
            return 'RESOLVED'
        elif self.status in ISSUE_STATE_UNRESOLVED:
            return 'NEW'
        return 'NEW'

    def is_unassigned(self):
        return self.status in ('unstarted', 'rejected')


pivotaltracker_converter = Converter(
    id='id',
    desc='desc',
    reporter='reporter',
    owner='owner',
    status='status',
    resolution=lambda d: '',
    project_name='project_name',
    opendate=lambda d: dateutil.parser.parse(d['opendate']),
    changeddate=lambda d: dateutil.parser.parse(d['changeddate']),
    priority='priority',
    severity='priority',
    component_name='component',
    deadline='deadline',
    whiteboard='whiteboard',
)


class PivotalTrackerTokenFetcher(BaseFetcher):
    TOKEN_MEMCACHE_KEY = '{tracker_type}-{tracker_id}-{user_id}-pivotal_token'
    TOKEN_MEMCACHE_TIMEOUT = 60*60*24

    _token_url = 'https://www.pivotaltracker.com/services/v3/tokens/active'
    _token = None
    bug_class = PivotalTrackerBug
    get_converter = lambda self: pivotaltracker_converter

    def __init__(self, tracker, credentials, login_mapping):
        super(PivotalTrackerTokenFetcher, self).__init__(tracker, credentials, login_mapping)
        try:
            email, login = credentials.login.split(';')
        except Exception:
            email, login = '', ''
        self.email = email
        self.login = login
        self.login_mapping = dict([
            (k.split(';')[1], v) for k, v in login_mapping.iteritems() if ';' in k
        ])

    def get_headers(self):
        headers = super(PivotalTrackerTokenFetcher, self).get_headers()
        if self._token:
            headers['X-TrackerToken'] = [self._token]
        return headers

    def fetch_token(self, callback):
        headers = self.get_headers()
        credentials = base64.encodestring('%s:%s' % (self.email, self.password))
        headers['Authorization'] = ["Basic %s" % credentials]
        self.request(
            self._token_url,
            headers,
            partial(self.responded, on_success=partial(self.parse_token, callback)),
        )

    def get_token(self, callback):
        if not self._token:
            key = self.TOKEN_MEMCACHE_KEY.format(tracker_type=self.tracker.type, tracker_id=self.tracker.id, user_id=self.user.id)
            token = memcache.get(key)
            if not token:
                self.fetch_token(callback)
            else:
                self._token = token
                callback()
        else:
            callback()

    def parse_token(self, callback, data):
        key = self.TOKEN_MEMCACHE_KEY.format(tracker_type=self.tracker.type, tracker_id=self.tracker.id, user_id=self.user.id)
        data = ET.fromstring(data)
        self._token = data.find('guid').text
        memcache.set(key, self._token, timeout=self.TOKEN_MEMCACHE_TIMEOUT)
        callback()


class PivotalTrackerFetcher(PivotalTrackerTokenFetcher):

    api_url = 'services/v5/projects'
    default_fields = 'owned_by,requested_by,estimate,:default'

    def __init__(self, *args, **kwargs):
        super(PivotalTrackerFetcher, self).__init__(*args, **kwargs)
        self._project_ids = None

    def prepare_url(self, project_id='', endpoint='', params={}):
        tracker_url = self.tracker.url.replace('http://', 'https://')
        url = make_path(tracker_url, self.api_url, project_id, endpoint)
        if params:
            url += '?'
            url = serialize_url(url, **params)
        return url

    def fetch(self, endpoint, params={}, callback=None, project_selector=None):
        if not self._token:
            self_callback = partial(
                self.fetch,
                endpoint,
                params=params,
                callback=callback,
                project_selector=project_selector,
            )
            self.get_token(self_callback)
        elif self._project_ids is None:
            self_callback = partial(
                self.fetch,
                endpoint,
                params=params,
                callback=callback,
                project_selector=project_selector,
            )
            if project_selector:
                self._project_ids = [project_selector, ]
                self_callback()
            else:
                self.get_projects(self_callback)
        else:
            headers = self.get_headers()
            callback = callback or self.responded
            for project_id in self._project_ids:
                url = self.prepare_url(project_id, endpoint, params)
                self.request(url, headers, callback)

    def get_projects(self, callback):
        headers = self.get_headers()
        url = self.prepare_url()
        self.request(
            url,
            headers,
            partial(
                self.responded,
                on_success=partial(self.parse_project, callback),
            )
        )

    def parse_project(self, callback, data):
        project_json = json.loads(data)
        self._project_ids = [p['id'] for p in project_json]
        callback()

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

    @cached_bug_fetcher(lambda: u'user')
    def fetch_user_tickets(self):
        params = {
            'fields': self.default_fields,
            'filter': self._get_filters(
                owners=[self.login],
                states=ISSUE_STATE_UNRESOLVED
            )
        }
        self.fetch('stories', params=params)

    @cached_bug_fetcher(lambda: u'all')
    def fetch_all_tickets(self):
        params = {
            'fields': self.default_fields,
            'filter': self._get_filters(
                owners=self.login_mapping.keys(),
                states=ISSUE_STATE_UNRESOLVED,
                include_done=True,
            )
        }
        self.fetch('stories', params=params)

    @cached_bug_fetcher(lambda: u'user-resolved')
    def fetch_user_resolved_tickets(self):
        params = {
            'fields': self.default_fields,
            'filter': self._get_filters(
                owners=[self.login],
                states=ISSUE_STATE_RESOLVED,
                include_done=True,
            )
        }
        self.fetch('stories', params=params)

    @cached_bug_fetcher(lambda: u'all-resolved')
    def fetch_all_resolved_tickets(self):
        params = {
            'fields': self.default_fields,
            'filter': self._get_filters(
                owners=self.login_mapping.keys(),
                states=ISSUE_STATE_RESOLVED,
                include_done=True,
            )
        }
        self.fetch('stories', params=params)

    def fetch_bugs_for_query(
            self, ticket_ids, project_selector,
            component_selector, version):
        params = {
            'fields': self.default_fields,
            'filter': self._get_filters(
                owners=self.login_mapping.keys(),
                ids=ticket_ids,
                include_done=True,
            )
        }
        self.fetch(
            'stories',
            params=params,
            project_selector=project_selector,
        )

    def fetch_resolved_bugs_for_query(
            self, ticket_ids, project_selector,
            component_selector, version):
        params = {
            'fields': self.default_fields,
            'filter': self._get_filters(
                owners=self.login_mapping.keys(),
                ids=ticket_ids,
                states=ISSUE_STATE_RESOLVED,
                include_done=True,
            )
        }
        self.fetch(
            'stories',
            params=params,
            project_selector=project_selector,
        )

    def fetch_scrum(self, sprint_name, project_id=None, component_id=None):
        params = {
            'fields': self.default_fields,
            'filter': self._get_filters(
                label=sprint_name,
                include_done=True,
            )
        }
        self.fetch('stories', params=params, project_selector=project_id)

    def fetch_bug_titles_and_depends_on(self, ticket_ids):
        ids = []
        for id_ in ticket_ids:
            if id_:
                ids.append(str(id_))
        params = {
            'filter': self._get_filters(
                ids=ids,
                include_done=True,
            )
        }
        callback = partial(
            self.responded,
            on_success=self.ticket_title_response
        )
        self.fetch('stories', params=params, callback=callback)

    def ticket_title_response(self, data):
        try:
            for bug in self._parse(data):
                self.bugs[bug.id] = dict(
                    title=bug.desc,
                )
        except BaseException, e:
            EXCEPTION(u"Could not parse tracker response")
            self.fail(e)
        else:
            self.success()

    def _parse(self, data):
        stories = json.loads(data)
        converter = self.get_converter()
        for story in stories:
            points = story.get('estimate')
            points = int(points) if points else 0

            project_name = str(story['project_id'])

            owned_by = story.get('owned_by')
            owner = owned_by.get('name') if owned_by else ''

            bug_desc = dict(
                tracker=self.tracker,
                id=story['id'],
                desc=story['name'],
                reporter=story['requested_by']['name'],
                owner=owner,
                status=story['current_state'],
                project_name=project_name,
                opendate=story['created_at'],
                changeddate=story['updated_at'],
                whiteboard={
                    'p': points,
                },
            )
            yield self.bug_class(
                tracker=self.tracker,
                **converter(bug_desc)
            )

    def received(self, data):
        try:
            for bug in self._parse(data):
                self.bugs[bug.id] = bug
        except BaseException, e:
            EXCEPTION(u"Could not parse tracker response")
            self.fail(e)
        else:
            if len(self._project_ids) == 1:
                self.success()
            else:
                self._project_ids.pop()
