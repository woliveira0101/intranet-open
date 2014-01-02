# -*- coding: utf-8 -*-
"""

"""
import json
from intranet3.asyncfetchers import base
from intranet3.helpers import Converter, serialize_url
from dateutil.parser import parse
from intranet3.asyncfetchers.base import BaseFetcher, BasicAuthMixin, cached_bug_fetcher
from intranet3.log import INFO_LOG, EXCEPTION_LOG

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)

class BitBucketBug(base.Bug):
    def get_url(self):
        return u'%s/issue/%s' % (
            self.tracker.url.replace('https://api.bitbucket.org/1.0/repositories/', 'https://bitbucket.org/'),
            self.id
        )

bitbucket_converter = Converter(
    id='local_id',
    desc='title',
    reporter=lambda d: d['reported_by']['username'],
    owner=lambda d: d['responsible']['username'],
    priority='priority',
    severity='priority',
    status='status',
    project_name=lambda d: 'none',
    component_name=lambda d: d['metadata']['component'] or 'none',
    deadline='deadline',
    opendate=lambda d: parse(d.get('utc_created_on', '')),
    changeddate=lambda d: parse(d.get('utc_last_updated', '')),
    dependson=lambda d: {},
    blocked=lambda d: {}
)

def _fetcher_function(resolved, single):
    @cached_bug_fetcher(lambda: u'resolved-%s-single-%s' % (resolved, single))
    def fetcher(self):
        if resolved:
            # bitbucked doesn't have resolved not-closed
            self.success()
            return
        params = self.common_url_params()
        params.update(self.single_user_params() if single else self.all_users_params())
        url = serialize_url(self.tracker.url + '/issues?', **params)
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

class BitBucketFetcher(BasicAuthMixin, BaseFetcher):
    
    bug_class = BitBucketBug
    get_converter = lambda self: bitbucket_converter
    
    def parse(self, data):
        converter = self.get_converter()
        json_data = json.loads(data)
        for bug_desc in json_data['issues']:
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
            status=['open', 'new'],
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
        except BaseException, e:
            EXCEPTION(u"Could not parse tracker response")
            self.fail(e)
        else:
            self.success()

