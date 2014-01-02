# coding: utf-8
import json
import re
from functools import partial
from intranet3 import memcache

from intranet3.asyncfetchers import base
from intranet3.helpers import Converter, serialize_url
from dateutil.parser import parse
from intranet3.asyncfetchers.base import BaseFetcher, BasicAuthMixin, cached_bug_fetcher
from intranet3.log import INFO_LOG, EXCEPTION_LOG

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)


class GithubBug(base.Bug):

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


def _fetcher_function(resolved, single):
    @cached_bug_fetcher(lambda: u'resolved-%s-single-%s' % (resolved, single))
    def fetcher(self):
        if resolved:
            # Github doesn't have open resolved
            self.success()
            return

        params = self.common_url_params()
        extra = self.single_user_params() if single else self.all_users_params()
        params.update(extra)

        url = serialize_url(self.tracker.url + 'issues?', **params)
        self.fetch(url)
    return fetcher

def _query_fetcher_function(resolved):
    def fetcher(self, ticket_ids, project_selector, component_selector,
                version):
        if resolved:
            # bitbucked doesn't have resolved not-closed
            self.success()
            return

        params = self.common_url_params()
        if ticket_ids:
            # query not supported by bitbucket - we will do it manually later
            self.wanted_ticket_ids = ticket_ids
        else:
            if project_selector and component_selector:
                uri = self.tracker.url + "repos/%s/%s/issues?" % (project_selector, component_selector[0])
                url = serialize_url(uri, **params)

        self.fetch(url)
    return fetcher


class GithubFetcher(BasicAuthMixin, BaseFetcher):
    bug_class = GithubBug
    get_converter = lambda self: github_converter

    MILESTONES_KEY = 'milestones_map' #klucz do mapowania nazwa_milestonea -> numer milestonea
    MILESTONES_TIMEOUT = 60*3

    def __init__(self, *args, **kwargs):
        super(GithubFetcher, self).__init__(*args, **kwargs)
        self.milestones = None
        self.issues_types_left = ['close', 'open']


    def parse(self, data):
        converter = self.get_converter()
        json_data = json.loads(data)

        for bug_desc in json_data:
            # Filter bugs
            convertered_data = converter(bug_desc)
            yield self.bug_class(
                tracker=self.tracker,
                **convertered_data
            )

    def fetch_milestones(self, callback, url):
        if self.milestones is None:
            self.milestones = memcache.get(self.MILESTONES_KEY)
            if self.milestones is None:
                url = str(url)
                self.request(
                    url,
                    self.get_headers(),
                    partial(self.responded, on_success=partial(self.parse_milestones, callback)),
                )
                return
            else:
                callback()

    def parse_milestones(self, callback, data):
        milestone_map = {}
        json_data = json.loads(data)
        for milestone in json_data:
            milestone_map[milestone['title']] = str(milestone['number'])

        memcache.set(
            self.MILESTONES_KEY,
            milestone_map,
            timeout=self.MILESTONES_TIMEOUT
        )
        self.milestones = milestone_map
        callback()

    def fetch(self, url):
        self.request(
            url,
            self.get_headers(),
            partial(self.responded)
        )

    def fetch_scrum(self, sprint_name, project_id=None, component_id=None):
        base_url = '%srepos/%s/%s/' % (self.tracker.url, project_id, component_id)
        milestones_url = ''.join((base_url, 'milestones'))
        issues_url = ''.join((base_url, 'issues?'))
        if self.milestones is None:
            self.fetch_milestones(partial(self.fetch_scrum, sprint_name, project_id, component_id), milestones_url)
        elif self.milestones == {}:
            return self.fail('No milestones')
        else:
            opened_bugs_url = serialize_url(
                issues_url,
                **dict(
                        milestone = self.milestones.get(sprint_name),
                        state = 'open'
                )
            )

            closed_bugs_url = serialize_url(
                issues_url,
                **dict(
                        milestone = self.milestones.get(sprint_name),
                        state = 'closed'
                )
            )

            self.fetch(opened_bugs_url)
            self.fetch(closed_bugs_url)

    def common_url_params(self):
        return dict(
            state='open',
            format='json'
        )

    def single_user_params(self):
        return dict(
            filter='assigned'
        )

    def all_users_params(self):
        return dict(
            filter='all'
        )

    fetch_user_tickets = _fetcher_function(resolved=False, single=True)
    """ Start fetching tickets for current user """
    fetch_all_tickets = _fetcher_function(resolved=False, single=False)
    """ Start fetching tickets for all users in mapping """
    fetch_user_resolved_tickets = _fetcher_function(resolved=True, single=True)
    fetch_all_resolved_tickets = _fetcher_function(resolved=True, single=False)
    fetch_bugs_for_query = _query_fetcher_function(resolved=False)
    fetch_resolved_bugs_for_query = _query_fetcher_function(resolved=True)

    def received(self, data):
        """ Called when server returns whole response body """
        try:
            has_wanted = hasattr(self, 'wanted_ticket_ids')
            for bug in self.parse(data):
                if has_wanted and bug.id not in self.wanted_ticket_ids:
                    continue # manually skip unwanted tickets

                self.bugs[bug.number] = bug
        except BaseException as e:
            EXCEPTION(u"Could not parse tracker response")
            self.fail(e)
            return

        if self.milestones:
            self.issues_types_left.pop()
            if len(self.issues_types_left) == 0:
                self.success()
        else:
            self.success()