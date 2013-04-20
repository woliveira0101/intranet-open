import csv
from dateutil.parser import parse
from functools import partial

from intranet3.asyncfetchers.base import ( BaseFetcher, CSVParserMixin,
    BasicAuthMixin, Bug, cached_bug_fetcher, SimpleProtocol, FetchException)
from intranet3.helpers import Converter, serialize_url
from intranet3.log import INFO_LOG, EXCEPTION_LOG
from intranet3.helpers import decoded_dict

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)

class TracBug(Bug):
    
    def get_url(self, number=None):
        number = number if number else self.id
        return self.tracker.url + '/ticket/' + number


def get_depends_on(bug_desc):
    if 'blockedby' in bug_desc:
        deps = bug_desc['blockedby']
    elif 'dependencies' in bug_desc:
        deps = bug_desc['dependencies']
    else:
        return []
    output = []
    for dep in deps.split(', '):
        try:
            id = int(dep)
        except ValueError: # nl trac can return '--'
            continue
        else:
            output.append(str(id))
    return output


trac_converter = Converter(
    id='id',
    desc='summary',
    reporter='reporter',
    owner='owner',
    priority=lambda d: d.get('priority') or d.get('severity'),
    severity=lambda d: d.get('priority') or d.get('severity'),
    status='status',
    resolution=lambda d: '',
    project_name=lambda d: d.get('client_name', 'none'),
    component_name='component',
    deadline='deadline',
    opendate=lambda d: parse(d.get('time', '')),
    changeddate=lambda d: parse(d.get('changetime', '')),
    dependson=lambda d: dict((bug, {'resolved': False}) for bug in get_depends_on(d) if bug),
    blocked=lambda d: dict((bug, {'resolved': False}) for bug in d.get('blocking', '').split(', ') if bug)
)

def _fetcher_function(resolved, single):
    @cached_bug_fetcher(lambda: u'resolved-%s-single-%s' % (resolved, single))
    def fetcher(self):
        params = self.resolved_common_url_params() if resolved else self.common_url_params()
        params.update(self.single_user_params() if single else self.all_users_params())
        if resolved:
            params['reporter'] = params['owner']
            del params['owner']
        url = serialize_url(self.tracker.url + '/query?', **params)
        self.fetch(url)
    return fetcher

def _query_fetcher_function(resolved):
    def fetcher(self, ticket_ids, project_selector, component_selector, version):
        params = self.resolved_common_url_params() if resolved else self.common_url_params()
        if ticket_ids:
            params.update(id=[str(id) for id in ticket_ids])
        else:
            if project_selector:
                params.update(client_name=project_selector)
                if component_selector:
                    params.update(component=component_selector)
        url = serialize_url(self.tracker.url + '/query?', **params)
        self.fetch(url)
    return fetcher

class TracFetcher(BasicAuthMixin, CSVParserMixin, BaseFetcher):
    
    bug_class = TracBug
    get_converter = lambda self: trac_converter
    
    def fetch(self, url):
        headers = self.get_headers()
        self.request(url, headers, self.responded)
        
    def common_url_params(self):
        return dict(
            max='1000',
            status=['assigned', 'new', 'reopened'],
            order='priority',
            col=['id', 'summary', 'status', 'type', 'priority', 'severity', 'milestone', 'component', 'reporter', 'owner', 'client_name', 'time', 'changetime', 'blockedby', 'dependencies', 'blocking'],
            format='csv'
        )

    def resolved_common_url_params(self):
        params = self.common_url_params()
        params.update(dict(
            resolution=['fixed'],
            status=['resolved', 'verified'],
        ))
        return params
        
    def single_user_params(self):
        return dict(
            owner=self.login
        )

    def all_users_params(self):
        return dict(
            owner=self.login_mapping.keys()
        )
        
    fetch_user_tickets = _fetcher_function(resolved=False, single=True)
    """ Start fetching tickets for current user """

    fetch_all_tickets = _fetcher_function(resolved=False, single=False)
    """ Start fetching tickets for all users in mapping """

    fetch_user_resolved_tickets = _fetcher_function(resolved=True, single=True)

    fetch_all_resolved_tickets = _fetcher_function(resolved=True, single=False)
    
    fetch_bugs_for_query = _query_fetcher_function(resolved=False)
    
    fetch_resolved_bugs_for_query = _query_fetcher_function(resolved=True)
    
    def _fetch_tickets_by_ids(self, ticket_ids, callback):
        params = dict(
            max='1000',
            col=['id', 'blockedby', 'dependencies', 'priority', 'severity', 'resolution', 'summary'],
            format='csv'
        )
        ids = []
        if ticket_ids:
            for id in ticket_ids:
                if id:
                    ids.append(str(id))
            params['id'] = ids
        if not ids:
            return self.success()
        url = serialize_url(self.tracker.url + '/query?', **params)
        headers = self.get_headers()
        self.request(url, headers, partial(self.parse_response, callback))
    
    def fetch_dependons_for_ticket_ids(self, ticket_ids):
        self._fetch_tickets_by_ids(ticket_ids, self.parse_dependons_for_ticket_ids_cvs)
        
    def fetch_bug_titles_and_depends_on(self, ticket_ids):
        self._fetch_tickets_by_ids(ticket_ids, self.parse_bug_titles_and_depends_on_csv)

    def get_severity(self, bug_desc):
        return bug_desc.get('severity', '') or bug_desc.get('priority', '')

    def is_bug(self, bug_desc):
        """ Check if given XML bug definition adheres to "bug" definition from #69234 """
        severity = self.get_severity(bug_desc)
        resolution = bug_desc.get('resolution', '')

        return (not severity in ('enhancement high', 'enhancement medium', 'enhancement low')) \
               and (not resolution == 'invalid')
    
    def _parse_tickets_csv_response(self, data, bug_callback, success_callback):
        try:
            reader = csv.DictReader(data.split('\n'), delimiter=self.delimiter)
            for bug_desc in reader:
                bug_callback(bug_desc)
        except BaseException, e:
            EXCEPTION(u'Parse csv response failed for data %r' % data)
            self.failed(e)
        else:
            success_callback()
               
    def parse_bug_titles_and_depends_on_csv(self, data):
        """ Parse response for query for bug titles and depends on """
        def handle(bug_desc):
            bug_id = bug_desc['id']
            depends = get_depends_on(bug_desc)
            summary = bug_desc.get('summary', '')
            is_bug = self.is_bug(bug_desc)
            self.bugs[bug_id] = {'title': summary, 'depends_on': depends, 'is_bug': is_bug, 'severity': self.get_severity(bug_desc)}
        
        self._parse_tickets_csv_response(data, handle, self.success)

    def parse_dependons_for_ticket_ids_cvs(self, data):
        """ Parse response for query of depends on """
        dependsons = []
        
        def handle(bug_desc):
            if self.is_bug(bug_desc):
                bug_id = bug_desc.get('id')
                blockedby = get_depends_on(bug_desc)
                self.bugs[bug_id] = True
            
                for id in blockedby:
                    if not self.bugs.get(id) and id:
                        dependsons.append(id)
        def on_success():
            if not dependsons:
                self.success()
            else:
                self.fetch_dependons_for_ticket_ids(dependsons)
        
        self._parse_tickets_csv_response(data, handle, on_success)

    def parse_dependson_and_blocked_bugs_csv(self, data):
        try:
            reader = csv.DictReader(data.split('\n'), delimiter=self.delimiter)
            for bug_desc in reader:
                bug_desc = decoded_dict(bug_desc, encoding=self.encoding)
                status = bug_desc.get('status')
                bug_id = bug_desc.get('id')
                summary = bug_desc.get('summary')

                if status:
                    self.dependson_and_blocked_status[bug_id]['resolved'] = status in ('closed', 'resolved', 'verified')
                if summary:
                    self.dependson_and_blocked_status[bug_id]['desc'] = summary
           
        except BaseException, e:
            self.failed(e)
        else:
            self.update_depensons_and_blocked_status()
            self.success()
    
    def parse_response(self, on_success, resp):
        """ Called when server returns response headers """
        if resp.code == 200:
            resp.deliverBody(SimpleProtocol(on_success, self.failed))
        else:
            self.fail(FetchException(u'Received xml response of resolution %s' % (resp.code, )))
    
    def get_status_of_dependson_and_blocked_bugs(self):
        for bug in self.bugs.itervalues():
            self.dependson_and_blocked_status.update(bug.dependson)
            self.dependson_and_blocked_status.update(bug.blocked)
        
        bug_ids = self.dependson_and_blocked_status.keys()
        if bug_ids:
            url = serialize_url('%s/query?' % self.tracker.url,
                                col=['id', 'status', 'summary'],
                                id=','.join(bug_ids),
                                format='csv')
            
            headers = self.get_headers()
            self.request(url, headers, partial(self.parse_response, self.parse_dependson_and_blocked_bugs_csv))
        else:
            self.success()

    def received(self, data):
        """ Called when server returns whole response body """
        try:
            for bug in self.parse(data):
                self.bugs[bug.id] = bug
            self.get_status_of_dependson_and_blocked_bugs()
        except BaseException, e:
            EXCEPTION(u"Could not parse tracker response")
            self.fail(e)

