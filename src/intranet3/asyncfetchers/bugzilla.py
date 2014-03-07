from functools import partial
from dateutil.parser import parse
from xml.etree import ElementTree as ET

from pyramid.decorator import reify

from intranet3.asyncfetchers.base import ( BaseFetcher, CSVParserMixin,
    SimpleProtocol, BasicAuthMixin,
    FetchException, Bug, cached_bug_fetcher )
from intranet3 import helpers as h
from intranet3.log import EXCEPTION_LOG, INFO_LOG


LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)


class BugzillaBug(Bug):

    def get_url(self, number=None):
        number = number if number else self.id
        return self.tracker.url + '/show_bug.cgi?id=%(id)s' % {'id': number}

    def is_unassigned(self):
        return not self.owner or not self.owner.email.endswith('stxnext.pl')

    @reify
    def is_blocked(self):
        wb_blocked = self.whiteboard.get('blocked')
        if wb_blocked in h.positive_values:
            return True

        if wb_blocked is None: # blocked param is not set
            for bug_data in self.dependson.values():
                if bug_data.get('resolved', True) is False:
                    return True

        return False

    def get_status(self):
        return self.status

    def get_resolution(self):
        return self.resolution


bugzilla_converter = h.Converter(
        id='bug_id',
        desc='short_desc',
        reporter='reporter',
        owner='assigned_to',
        priority=lambda d: d.get('priority', ''), # + '/' + d['priority'],
        severity=lambda d: d.get('bug_severity', ''),
        status=lambda d: d.get('bug_status', ''), # + '/' + d['resolution'],
        resolution=lambda d: d.get('resolution', ''),
        project_name='product',
        component_name='component',
        deadline='deadline',
        opendate=lambda d: parse(d.get('opendate', '')),
        changeddate=lambda d: parse(d.get('changeddate', '')),
        whiteboard='status_whiteboard',
        version='version',
    )

def _fetcher_function(resolved, single):
    @cached_bug_fetcher(lambda: u'resolved-%s-single-%s' % (resolved, single))
    def fetcher(self):
        params = self.resolved_common_url_params() \
            if resolved else self.common_url_params()
        params.update(self.single_user_params() if
                      single else self.all_users_params())
        url = '%s/buglist.cgi' % self.tracker.url
        self.fetch_post(url, params)
    return fetcher

def _query_fetcher_function(**conditions):
    def fetcher(self, ticket_ids, project_selector, component_selector,
                version):
        params = dict(
            ctype='csv'
        )
        params.update(conditions)
        if ticket_ids:
            params.update(bug_id=','.join(str(id) for id in ticket_ids))
        else:
            if project_selector:
                params.update(product=project_selector)
                if component_selector:
                    params.update(component=component_selector)
        url = '%s/buglist.cgi' % self.tracker.url
        self.fetch_post(url, params)
    return fetcher


class BugzillaFetcher(BasicAuthMixin, CSVParserMixin, BaseFetcher):
    """ Fetcher for Bugzilla bugs """

    redirect_support = True
    SPRINT_REGEX = '[[:<:]]s=%s[[:>:]]'

    COLUMNS = ('bug_severity', 'assigned_to', 'version',
            'bug_status', 'resolution', 'product', 'op_sys', 'short_desc',
            'reporter', 'opendate', 'changeddate', 'component', 'deadline',
            'bug_severity', 'product', 'priority', 'status_whiteboard')

    COLUMNS_COOKIE = 'COLUMNLIST=' + "%20".join(COLUMNS)

    bug_class = BugzillaBug
    get_converter = lambda self: bugzilla_converter

    def get_headers(self):
        headers = super(BugzillaFetcher, self).get_headers()
        headers['Cookie'] = [self.COLUMNS_COOKIE]
        return headers

    def fetch(self, url):
        headers = self.get_headers()
        self.request(url, headers, self.responded)

    def fetch_post(self, url, params, on_success=None):
        if not on_success:
            on_success = self.responded
        url = url.encode('utf-8')
        body = h.serialize_url('', **params)
        headers = self.get_headers()
        self.request(url, headers, on_success, method='POST', body=body)

    def common_url_params(self):
        return dict(
            bug_status=['NEW', 'ASSIGNED', 'REOPENED', 'UNCONFIRMED',
                        'CONFIRMED', 'WAITING'],
            ctype='csv',
            emailassigned_to1='1'
        )

    def resolved_common_url_params(self):
        return {
            'bug_status':['RESOLVED', 'VERIFIED'],
            'ctype':'csv',
            'emailreporter1':'1',
            'field0-0-0':'resolution',
            'type0-0-0':'notequals',
            'value0-0-0':'LATER'
        }

    def single_user_params(self):
        return dict(
            emailtype1='exact',
            email1=self.login
        )

    def all_users_params(self):
        return dict(
            emailtype1='regexp',
            email1='(' + '|'.join(self.login_mapping.keys()) + ')'
        )

    fetch_user_tickets = _fetcher_function(resolved=False, single=True)
    """ Start fetching tickets for current user """

    fetch_all_tickets = _fetcher_function(resolved=False, single=False)
    """ Start fetching tickets for all users in mapping """

    fetch_user_resolved_tickets = _fetcher_function(resolved=True, single=True)

    fetch_all_resolved_tickets = _fetcher_function(resolved=True, single=False)

    fetch_bugs_for_query = _query_fetcher_function(
        bug_status=['NEW', 'ASSIGNED', 'REOPENED', 'UNCONFIRMED', 'CONFIRMED',
                    'WAITING']
    )

    fetch_resolved_bugs_for_query = _query_fetcher_function(
        bug_status=['RESOLVED', 'VERIFIED']
    )

    fetch_all_bugs_for_query = _query_fetcher_function()

    def fetch_scrum(self, sprint_name, project_id=None, component_id=None):
        params = dict(
            ctype='csv',
            status_whiteboard_type='regexp',
            status_whiteboard=self.SPRINT_REGEX % sprint_name,
            bug_status=[
                'NEW',
                'ASSIGNED',
                'REOPENED',
                'UNCONFIRMED',
                'CONFIRMED',
                'WAITING',
                'RESOLVED',
                'VERIFIED',
                'CLOSED'
            ],
        )
        url = '%s/buglist.cgi' % self.tracker.url
        self.fetch_post(url, params)

    def fetch_bug_titles_and_depends_on(self, ticket_ids):
        params = dict(
            ctype='xml',
            field=['dependson', 'bug_id', 'short_desc', 'bug_severity',
                   'resolution'],
            id=[str(id_) for id_ in ticket_ids],
        )
        url = '%s/show_bug.cgi' % self.tracker.url
        self.fetch_post(
            url,
            params,
            on_success=partial(
                self.xml_response,
                self.parse_response_of_bug_titles_and_depends_on
            ),
        )

    def fetch_dependons_for_ticket_ids(self, ticket_ids):
        params = dict(
            ctype='xml',
            field=['dependson', 'bug_id', 'bug_severity', 'resolution']
        )
        if ticket_ids:
            ids = [str(id_) for id_ in ticket_ids if id_]
            params.update(id=ids)
        if not ids:
            return self.fail(FetchException(u'Ticket ids list is empty'))
        url = '%s/show_bug.cgi' % self.tracker.url
        self.fetch_post(
            url,
            params,
            on_success=partial(
                self.xml_response,
                self.parse_response_of_dependons_for_ticket_ids,
            ),
        )

    def _parse_xml_response(self, data, bug_callback, success_callback):
        """ Parse xml """
        try:
            # igozilla returns iso-8859-2, but does not declare it
            data = data.replace(
                '<?xml version="1.0" standalone="yes"?>',
                '<?xml version="1.0" encoding="iso-8859-2" standalone="yes"?>'
            )
            xml = ET.fromstring(data)
            for bug in xml.findall('bug'):
                bug_callback(bug)
        except BaseException, e:
            EXCEPTION(u'Parse xml response failed for data %r' % data)
            self.failed(e)
        else:
            success_callback()

    def parse_response_of_bug_titles_and_depends_on(self, data):
        """ Parse response for query of bug titles and depends on """
        def handle(bug):
            bug_id = bug.find('bug_id').text
            short_desc = getattr(bug.find('short_desc'), 'text', '')
            depends_on = [item.text for item in bug.findall('dependson')]
            is_bug = self.is_bug(bug)
            self.bugs[bug_id] = {
                'title': short_desc,
                'depends_on': depends_on,
                'is_bug': is_bug,
                'severity': getattr(bug.find('bug_severity'),'text', '')
            }

        self._parse_xml_response(data, handle, self.success)

    def get_severity(self, bug):
        return getattr(bug.find('bug_severity'), 'text', '')

    def is_bug(self, bug):
        """
        Check if given XML bug definition adheres to "bug" definition
        from #69234
        """
        severity = self.get_severity(bug)
        resolution = getattr(bug.find('resolution'), 'text', '')
        return (not severity in ('enhancement high', 'enhancement medium',
                'enhancement low')) and (not resolution == 'INVALID')

    def parse_response_of_dependons_for_ticket_ids(self, data):
        """ Parse response for query of depends on """
        dependsons = []
        def handle(bug):
            if self.is_bug(bug):
                bug_id = bug.find('bug_id').text
                self.bugs[bug_id] = True

                for item in bug.findall('dependson'):
                    id = item.text
                    if not self.bugs.get(id) and id:
                        dependsons.append(id)

        def on_success():
            if not dependsons:
                self.success()
            else:
                self.fetch_dependons_for_ticket_ids(dependsons)

        self._parse_xml_response(data, handle, on_success)

    def update_bugs_statuses(self, xml):
        for bug in xml.findall('bug'):
            bug_id = bug.find('bug_id').text
            status = getattr(bug.find('bug_status'), 'text', None)
            description = getattr(bug.find('short_desc'), 'text', None)
            if status:
                self.dependson_and_blocked_status[bug_id]['resolved'] = \
                    status in ('CLOSED', 'RESOLVED', 'VERIFIED')
            if description:
                self.dependson_and_blocked_status[bug_id]['desc'] = description

    def parse_dependson_and_blocked_bugs_xml(self, data):
        try:
            # igozilla returns iso-8859-2, but does not declare it
            data = data.replace(
                '<?xml version="1.0" standalone="yes"?>',
                '<?xml version="1.0" encoding="iso-8859-2" standalone="yes"?>'
            )
            xml = ET.fromstring(data)
            self.update_bugs_statuses(xml)
        except BaseException, e:
            self.failed(e)
        else:
            self.update_depensons_and_blocked_status()
            self.success()

    def get_status_of_dependson_and_blocked_bugs(self):
        bug_ids = self.dependson_and_blocked_status.keys()
        if bug_ids:
            url = '%s/show_bug.cgi' % self.tracker.url
            params = dict(
                ctype='xml',
                id=bug_ids,
                field=['bug_status', 'bug_id', 'short_desc']
            )
            self.fetch_post(
                url,
                params,
                on_success=partial(
                    self.xml_response,
                    self.parse_dependson_and_blocked_bugs_xml
                ),
            )
        else:
            self.success()

    def parse_xml(self, data):
        try:
            # igozilla returns iso-8859-2, but does not declare it
            data = data.replace(
                '<?xml version="1.0" standalone="yes"?>',
                '<?xml version="1.0" encoding="iso-8859-2" standalone="yes"?>'
            )
            xml = ET.fromstring(data.decode(self.encoding))
            for bug in xml.findall('bug'):
                bug_id = bug.find('bug_id').text
                obj = self.bugs.get(bug_id)
                if obj:
                    for key in ('blocked', 'dependson'):
                        results = dict(
                            (item.text, {'resolved': False})
                            for item in bug.findall(key)
                        )
                        self.dependson_and_blocked_status.update(results)

                        if results:
                            setattr(obj, key, results)

        except BaseException, e:
            self.failed(e)
        else:
            self.get_status_of_dependson_and_blocked_bugs()

    def xml_failed(self, err):
        self.fail(err)
        EXCEPTION(u"XML for tracker %s failed: %s" % (self.tracker.name, err))

    def xml_response(self, on_success, resp):
        """ Called when server returns response headers """
        if resp.code == 200:
            resp.deliverBody(SimpleProtocol(on_success, self.xml_failed))
        else:
            self.fail(FetchException(u'Received xml response %s' % resp.code))

    def get_dependson_and_blocked_by(self):
        url = '%s/show_bug.cgi' % self.tracker.url
        params = dict(
            ctype='xml',
            id=self.bugs.keys(),
            field=['blocked', 'dependson', 'bug_id']
        )
        self.fetch_post(url, params, partial(self.xml_response, self.parse_xml))

    def received(self, data):
        """ Called when server returns whole response body """
        try:
            for bug in self.parse(data):
                self.bugs[bug.id] = bug
            self.get_dependson_and_blocked_by()
        except BaseException, e:
            EXCEPTION(u"Could not parse tracker response")
            self.fail(e)
