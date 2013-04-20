import base64
import datetime
import xml.etree.ElementTree as ET
from functools import partial

from intranet3.asyncfetchers.base import BaseFetcher, Bug, cached_bug_fetcher
from intranet3.helpers import Converter, serialize_url, make_path
from intranet3.log import EXCEPTION_LOG, INFO_LOG
from intranet3 import memcache

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)

ISSUE_STATE_RESOLVED = ['delivered', 'finished']
ISSUE_STATE_UNRESOLVED = ['started','unstarted','unscheduled']


class PivotalTrackerBug(Bug):

    def get_url(self, number=None):
        number = number if number else self.id
        return make_path(self.tracker.url, '/story/show', number)


pivotaltracker_converter = Converter(
    id='id',
    desc='desc',
    reporter='reporter',
    owner='owner',
    status='status',
    resolution=lambda d: '',
    project_name='project_name',
    opendate=lambda d: datetime.datetime.strptime(d['opendate'],'%Y/%m/%d %H:%M:%S %Z'),
    changeddate=lambda d: datetime.datetime.strptime(d['changeddate'],'%Y/%m/%d %H:%M:%S %Z'),
    priority='priority',
    severity='priority',
    component_name='component',
    deadline='deadline',
)


class PivotalTrackerTokenFetcher(BaseFetcher):
    TOKEN_MEMCACHE_KEY = '{tracker_type}-{tracker_id}-{user_id}-pivotal_token'
    TOKEN_MEMCACHE_TIMEOUT = 60*60*24

    _token_url = 'https://www.pivotaltracker.com/services/v3/tokens/active'
    _token = None
    bug_class = PivotalTrackerBug
    get_converter = lambda self: pivotaltracker_converter

    def get_headers(self):
        headers = super(PivotalTrackerTokenFetcher, self).get_headers()
        if self._token:
            headers['X-TrackerToken'] = [self._token]
        return headers

    def fetch_token(self, callback):
        headers = self.get_headers()
        credentials = base64.encodestring('%s:%s' % (self.login, self.password))
        headers['Authorization'] = ["Basic %s" % credentials]
        self.request(
            self._token_url,
            headers,
            partial(self.responded, on_success=partial(self.parse_token, callback)),
        )

    def get_token(self, callback):
        if not self._token:
            key =  self.TOKEN_MEMCACHE_KEY.format(tracker_type=self.tracker.type, tracker_id=self.tracker.id, user_id=self.user.id)
            token = memcache.get(key)
            if not token:
                self.fetch_token(callback)
            else:
                self._token = token
                callback()
        else:
            callback()

    def parse_token(self, callback, data):
        key =  self.TOKEN_MEMCACHE_KEY.format(tracker_type=self.tracker.type, tracker_id=self.tracker.id, user_id=self.user.id)
        data = ET.fromstring(data)
        self._token = data.find('guid').text
        memcache.set(key, self._token, timeout=self.TOKEN_MEMCACHE_TIMEOUT)

        callback()


class PivotalTrackerFetcher(PivotalTrackerTokenFetcher):

    _project_id = None
    api_url = 'services/v3/projects'

    def prepare_url(self, project_id='', endpoint='', filters={}):
        tracker_url = self.tracker.url.replace('http://', 'https://')
        url = make_path(tracker_url, self.api_url, project_id, endpoint) + '?'
        filter_param = ' '.join([ '%s:%s' % (filter_name, filter) for filter_name, filter in filters.iteritems()])
        full_url = serialize_url(url, filter=filter_param)
        return full_url

    def fetch(self, endpoint, filters={}, callback=None):
        if not self._token:
            self_callback = partial(self.fetch, endpoint, filters=filters, callback=callback)
            self.get_token(self_callback)
        elif not self._project_id:
            self_callback = partial(self.fetch, endpoint, filters=filters, callback=callback)
            self.get_project(self_callback)
        else:
            headers = self.get_headers()
            callback = callback or self.responded
            url = self.prepare_url(self._project_id, endpoint, filters)
            self.request(url, headers, callback)

    def get_project(self, callback):
        headers = self.get_headers()
        url = self.prepare_url()
        self.request(
            url,
            headers,
            partial(self.responded, on_success=partial(self.parse_project, callback)),
        )

    def parse_project(self, callback, data):
        xml = ET.fromstring(data)
        self._project_id = xml.find('project').find('id').text
        callback()

    @cached_bug_fetcher(lambda: u'user')
    def fetch_user_tickets(self):
        self.fetch('stories', filters=dict(
            owner='"%s"' % self.user.name,
            state=','.join(ISSUE_STATE_UNRESOLVED),
        ))

    @cached_bug_fetcher(lambda: u'all')
    def fetch_all_tickets(self):
        self.fetch('stories', filters=dict(
            state=','.join(ISSUE_STATE_UNRESOLVED),
        ))

    @cached_bug_fetcher(lambda: u'user-resolved')
    def fetch_user_resolved_tickets(self):
        self.fetch('stories', filters=dict(
            owner='"%s"' % self.user.name,
            state=','.join(ISSUE_STATE_RESOLVED),
        ))

    @cached_bug_fetcher(lambda: u'all-resolved')
    def fetch_all_resolved_tickets(self):
        self.fetch('stories', filters=dict(
            state=','.join(ISSUE_STATE_RESOLVED),
        ))

    def fetch_bugs_for_query(self, ticket_ids, project_selector, component_selector, version):
        self.fetch('stories', filters=dict(
            id=','.join(ticket_ids)
        ))

    def fetch_resolved_bugs_for_query(self, ticket_ids, project_selector, component_selector, version):
        self.fetch('stories', filters=dict(
            id=','.join(ticket_ids),
            state=','.join(ISSUE_STATE_RESOLVED),
        ))

    def fetch_bug_titles_and_depends_on(self, ticket_ids):
        ids = []
        for id in ticket_ids:
            if id:
                ids.append(str(id))
        self.fetch(
            'stories',
            filters=dict(
                includedone='true',
                id=','.join(ids)
            ),
            callback=partial(self.responded, on_success=self.ticket_title_response),
        )

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
        xml = ET.fromstring(data)
        converter = self.get_converter()
        self.users = {}
        for story in xml.findall('story'):
            if story.find('owned_by') is None:
                continue
            owner_name = story.find('owned_by').text
            bug_desc = dict(
                tracker=self.tracker,
                id=story.find('id').text,
                desc=story.find('name').text,
                reporter=story.find('requested_by').text,
                owner=owner_name,
                status=story.find('current_state').text,
                project_name=self.tracker.name,
                opendate=story.find('created_at').text,
                changeddate=story.find('updated_at').text,
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
            self.success()
