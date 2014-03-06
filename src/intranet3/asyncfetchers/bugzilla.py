import requests
from dateutil.parser import parse
from xml.etree import ElementTree as ET

from intranet3 import helpers as h
from intranet3.models import User
from .request import RPC
from .base import BaseFetcher, BasicAuthMixin, CSVParserMixin
from .bug import BaseBugProducer, ToDictMixin, BaseScrumProducer


class BlockedOrDependson(ToDictMixin):
    def __init__(self, bug_id, status, description, tracker):
        self.id = bug_id
        self.status = status
        self.desc = description
        self.resolved = self.status in ('CLOSED', 'RESOLVED', 'VERIFIED')
        self.url = tracker.url + '/show_bug.cgi?id=%s' % bug_id
        self.owner = User(name='unknown')


class BugzillaScrumProcuder(BaseScrumProducer):

    def parse_whiteboard(self, wb):
        wb = wb.strip().replace('[', ' ').replace(']', ' ')
        if wb:
            return dict(i.split('=', 1) for i in wb.split() if '=' in i)
        return {}

    def get_points(self, bug, tracker, login_mapping, parsed_data):
        wb = self.parse_whiteboard(parsed_data.get('whiteboard', ''))
        points = wb.get('p')
        if points and points.strip().isdigit():
            return int(points.strip())


class BugzillaBugProducer(BaseBugProducer):

    SCRUM_PRODUCER_CLASS = BugzillaScrumProcuder

    def parse(self, tracker, login_mapping, raw_data):
        d = raw_data

        dependson = [
            BlockedOrDependson(tracker=tracker, **item)
            for item in d.get('dependson', [])
        ]
        dependson = [bug for bug in dependson if not bug.resolved]
        blocked = [
            BlockedOrDependson(tracker=tracker, **item)
            for item in d.get('blocked', [])
        ]
        blocked = [bug for bug in blocked if not bug.resolved]

        return dict(
            id=d['bug_id'],
            desc=d['short_desc'],
            reporter=d['reporter'],
            owner=d['assigned_to'],
            priority=d.get('priority', ''),  # + '/' + d['priority'],
            severity=d.get('bug_severity', ''),
            status=d.get('bug_status', ''),  # + '/' + d['resolution'],
            resolution=d.get('resolution', ''),
            project_name=d['product'],
            component_name=d['component'],
            deadline=d['deadline'],
            opendate=parse(d.get('opendate', '')),
            changeddate=parse(d.get('changeddate', '')),
            whiteboard=d['status_whiteboard'],
            version=d['version'],
            dependson=dependson,
            blocked=blocked,
        )

    def get_url(self, tracker, login_mapping, parsed_data):
        return tracker.url + '/show_bug.cgi?id=%s' % parsed_data['id']


class FetchBlockedAndDependsonMixin(object):

    def pre_parse(self, data):
        # igozilla returns iso-8859-2, but does not declare it
        data = data.replace(
            '<?xml version="1.0" standalone="yes"?>',
            '<?xml version="1.0" encoding="iso-8859-2" standalone="yes"?>'
        )
        #data = data.decode(self.encoding)
        xml = ET.fromstring(data)
        return xml

    def parse_ids(self, data):
        xml = self.pre_parse(data)
        result = {}
        for bug in xml.findall('bug'):
            bug_id = bug.find('bug_id').text
            blocked = [el.text for el in bug.findall('blocked')]
            dependson = [el.text for el in bug.findall('dependson')]
            result[bug_id] = (blocked, dependson)
        return result

    def parse_statuses(self, data):
        xml = self.pre_parse(data)
        result = {}
        for bug in xml.findall('bug'):
            bug_id = bug.find('bug_id').text
            status = getattr(bug.find('bug_status'), 'text', None)
            description = getattr(bug.find('short_desc'), 'text', None)
            result[bug_id] = {
                'bug_id': bug_id,
                'status': status,
                'description': description,
            }
        return result

    def get_ids(self, ids):
        url = '%s/show_bug.cgi' % self.tracker.url
        params = dict(
            ctype='xml',
            id=ids,
            field=['blocked', 'dependson', 'bug_id']
        )
        s = requests.Session()
        self.set_auth(s)
        result = s.request('GET', url, params=params, verify=False)

        return self.parse_ids(result.content)

    def get_statuses(self, ids):
        url = '%s/show_bug.cgi' % self.tracker.url
        params = dict(
            ctype='xml',
            id=ids,
            field=['bug_status', 'bug_id', 'short_desc']
        )
        s = requests.Session()
        self.set_auth(s)
        result = s.request('GET', url, params=params, verify=False)

        return self.parse_statuses(result.content)

    def after_parsing(self, parsed_data):
        ids = [bug['bug_id'] for bug in parsed_data]
        blocked_and_dependson = self.get_ids(ids)
        blocked_and_dependson_ids = []
        for blocked, dependson in blocked_and_dependson.itervalues():
            blocked_and_dependson_ids.extend(blocked)
            blocked_and_dependson_ids.extend(dependson)

        bad_statuses = self.get_statuses(
            set(blocked_and_dependson_ids)
        )

        for bug_data in parsed_data:
            bug_id = bug_data['bug_id']
            blocked, dependson = blocked_and_dependson.get(bug_id, ([], []))
            bug_data['blocked'] = [
                bad_statuses[bug_id]
                for bug_id in blocked
            ]
            bug_data['dependson'] = [
                bad_statuses[bug_id]
                for bug_id in dependson
            ]

        return parsed_data


class BugzillaFetcher(FetchBlockedAndDependsonMixin,
                      CSVParserMixin, BasicAuthMixin, BaseFetcher):
    BUG_PRODUCER_CLASS = BugzillaBugProducer

    COLUMNS = (
        'bug_severity', 'assigned_to', 'version',
        'bug_status', 'resolution', 'product', 'op_sys', 'short_desc',
        'reporter', 'opendate', 'changeddate', 'component', 'deadline',
        'bug_severity', 'product', 'priority', 'status_whiteboard'
    )

    COLUMNS_COOKIE = "%20".join(COLUMNS)

    def common_url_params(self):
        return dict(
            bug_status=['NEW', 'ASSIGNED', 'REOPENED', 'UNCONFIRMED',
                        'CONFIRMED', 'WAITING'],
            ctype='csv',
            emailassigned_to1='1'
        )

    def resolved_common_url_params(self):
        return {
            'bug_status': ['RESOLVED', 'VERIFIED'],
            'ctype': 'csv',
            'emailreporter1': '1',
            'field0-0-0': 'resolution',
            'type0-0-0': 'notequals',
            'value0-0-0': 'LATER'
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

    def add_data(self, session):
        from requests.cookies import create_cookie
        session.cookies.set_cookie(
            create_cookie('COLUMNLIST', self.COLUMNS_COOKIE)
        )

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

        body = h.serialize_url('', **params)
        rpc = RPC(url=url, method='POST', data=body)
        self.consume(rpc)

    def fetch_user_tickets(self, resolved=False):
        params = self.resolved_common_url_params() \
            if resolved else self.common_url_params()
        params.update(self.single_user_params())

        url = '%s/buglist.cgi' % self.tracker.url
        body = h.serialize_url('', **params)
        rpc = RPC(url=url, method='POST', data=body)
        self.consume(rpc)

    def fetch_all_tickets(self, resolved=False):
        params = self.resolved_common_url_params() \
            if resolved else self.common_url_params()
        params.update(self.all_users_params())

        url = '%s/buglist.cgi' % self.tracker.url
        body = h.serialize_url('', **params)
        rpc = RPC(url=url, method='POST', data=body)
        self.consume(rpc)

    def fetch_bugs_for_query(self, ticket_ids=None, project_selector=None,
                             component_selector=None, version=None,
                             resolved=False):
        super(BugzillaFetcher, self).fetch_bugs_for_query(
            ticket_ids,
            project_selector,
            component_selector,
            version,
            resolved,
        )

        if resolved:
            bug_status = ['RESOLVED', 'VERIFIED']
        else:
            bug_status = [
                'NEW',
                'ASSIGNED',
                'REOPENED',
                'UNCONFIRMED',
                'CONFIRMED',
                'WAITING',
            ]

        params = dict(
            ctype='csv'
        )
        params['bug_status'] = bug_status
        if ticket_ids:
            params.update(bug_id=','.join(str(id) for id in ticket_ids))
        elif project_selector:
            params.update(product=project_selector)
            if component_selector:
                params.update(component=component_selector)
        url = '%s/buglist.cgi' % self.tracker.url
        body = h.serialize_url('', **params)
        rpc = RPC(url=url, method='POST', data=body)
        self.consume(rpc)
