# -*- coding: utf-8 -*-
"""
Github connector
"""
import json
from intranet3.asyncfetchers import base
from intranet3.helpers import Converter, serialize_url
from dateutil.parser import parse
from intranet3.asyncfetchers.base import BaseFetcher, BasicAuthMixin, cached_bug_fetcher
from intranet3.log import INFO_LOG, EXCEPTION_LOG

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)


class GithubBug(base.Bug):
    def get_url(self):
        return 'HAHAHA NIE'
        # return u'%s/issue/%s' % (
        #     self.tracker.url.replace('https://api.bitbucket.org/1.0/repositories/', 'https://bitbucket.org/'),
        #     self.id
        # )


github_converter = Converter(
    id='number',
    desc='title',
    reporter=lambda d: d['user']['login'],
    owner=lambda d: d['assignee']['login'],
    priority=lambda d: 'none',
    severity=lambda d: 'none',
    status='state',
    resolution=lambda d: 'none',
    project_name=lambda d: 'none',
    component_name=lambda d: d['milestone']['description'] or 'none',
    deadline=lambda d: 'none',
    opendate=lambda d: parse(d.get('created_at', '')),
    changeddate=lambda d: parse(d.get('updated_at', '')),
    dependson=lambda d: {},
    blocked=lambda d: {}
)


def _fetcher_function(resolved, single):
    @cached_bug_fetcher(lambda: u'resolved-%s-single-%s' % (resolved, single))
    def fetcher(self):
        if resolved:
            # Github doesn't have open resolved
            self.success()
            return
        params = self.common_url_params()
        # import ipdb;ipdb.set_trace()                         # BREAK HERE
        # params.update(self.single_user_params() if single else self.all_users_params())
        url = serialize_url(self.tracker.url + 'issues?', **params)
        self.fetch(url)
    return fetcher


def _query_fetcher_function(resolved):
    def fetcher(self, ticket_ids, project_selector, component_selector):
        if resolved:
            # bitbucked doesn't have resolved not-closed
            self.success()
            return
        params = self.common_url_params()
        if ticket_ids:
            # query not supported by bitbucket - we will do it manually later
            self.wanted_ticket_ids = ticket_ids
        else:
            # project selector is not supported in bitbucket
            if component_selector:
                params.update(component=component_selector)
        url = serialize_url(self.tracker.url + '/issues?', **params)
        self.fetch(url)
    return fetcher


class GithubFetcher(BasicAuthMixin, BaseFetcher):
    bug_class = GithubBug
    get_converter = lambda self: github_converter
    
    def parse(self, data):
        # import ipdb;ipdb.set_trace()                         # BREAK HERE
        converter = self.get_converter()
        json_data = json.loads(data)
        for bug_desc in json_data:
            yield self.bug_class(
                tracker=self.tracker,
                **converter(bug_desc)
            )

    def fetch(self, url):
        headers = self.get_headers()
        self.request(url, headers, self.responded)
        
    def common_url_params(self):
        return dict(
            limit='50',
            status='open',
            format='json'
        )

    def single_user_params(self):
        return dict(
            responsible=self.login
        )

    def all_users_params(self):
        return dict(
            responsible=self.login_mapping.keys()
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
                self.bugs[bug.id] = bug
        except BaseException as e:
            EXCEPTION(u"Could not parse tracker response")
            self.fail(e)
        else:
            self.success()

