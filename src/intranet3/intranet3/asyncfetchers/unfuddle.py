import json
import dateutil.parser

from pyramid.decorator import reify

from intranet3.helpers import (
    serialize_url,
    make_path
)
from intranet3.log import ERROR_LOG, INFO_LOG

from .base import (
    BaseFetcher,
    BasicAuthMixin,
    FetcherBadDataError,
    FetchException,
)
from .bug import BaseBugProducer, BaseScrumProducer
from .request import RPC
from .utils import parse_whiteboard

LOG = INFO_LOG(__name__)
ERROR = ERROR_LOG(__name__)

class UnfuddleScrumProcuder(BaseScrumProducer):

    def get_points(self, bug, tracker, login_mapping, parsed_data):
        wb = parse_whiteboard(parsed_data.get('whiteboard', ''))
        points = wb.get('p')
        if points and points.strip().isdigit():
            return int(points.strip())


class UnfuddleBugProducer(BaseBugProducer):
    SCRUM_PRODUCER_CLASS = UnfuddleScrumProcuder

    def parse(self, tracker, login_mapping, raw_data):
        return raw_data

    def get_url(self, tracker, login_mapping, parsed_data):
        id, project_id = parsed_data['id'], parsed_data['project_id']
        url = make_path(tracker.url, '/a#/projects/%s/tickets/by_number/%s')
        url = url % (project_id, id)
        return url

    def get_status(self, tracker, login_mapping, parsed_data):
        return parsed_data['status'].upper()


class UnfuddleMetadataFetcher(BasicAuthMixin, BaseFetcher):
    """
    Unfuddle returns user_id insted of username so
    we have to create new login mapping by fetching all users from unfuddle
    and then use it in self.parse
    """
    unfuddle_data = None
    UNFUDDLE_DATA_KEY = 'unfuddle_data'
    UNFUDDLE_DATA_TIMEOUT = 60*3
    DATA_API = '/api/v1/initializer.json'

    def before_fetch(self):
        url = self.tracker.url + self.DATA_API
        rpc = RPC(url=url)
        self.apply_auth(rpc)
        rpc.start()
        self._unfuddle_data_rpc = rpc

    @reify
    def unfuddle_data(self):
        response = self._unfuddle_data_rpc.get_result()

        try:
            jdata = json.loads(response.content)
        except ValueError as e:
            ERROR('Error while parsing unfuddle response: \n%s' % e)
            raise FetchException(e)

        users = self._get_users(jdata.get('people', []))
        projects = self._get_projects(jdata.get('projects', []))
        whiteboard_field_numbers = self._get_whiteboard_number(
            jdata.get('projects', [])
        )
        components = self._get_components(jdata.get('components', []))
        milestones = self._get_milestones(jdata.get('milestones', []))
        custom_fields = self._get_custom_fields(
            jdata.get('custom_field_values', [])
        )

        data = {
            'users': users,
            'projects': projects,
            'components': components,
            'milestones': milestones,
            'custom_fields': custom_fields,
            'whiteboard_field_numbers': whiteboard_field_numbers,
        }
        return data

    def _get_whiteboard_number(self, projects):
        result = {}
        for project in projects:
            for field_number in range(1, 4):
                ticket_filed_active = 'ticket_field%s_active' % field_number
                ticket_filed_title = 'ticket_field%s_title' % field_number
                ticket_filed_active = project[ticket_filed_active]
                if not ticket_filed_active:
                    continue
                ticket_filed_title = project[ticket_filed_title]
                if ticket_filed_title.lower().strip() == 'whiteboard':
                    result[project['id']] = field_number
        return result

    def _get_users(self, users):
        mapping = dict([
            (user['id'], user['username']) for user in users
        ])
        mapping[None] = 'nobody'
        return mapping

    def _get_projects(self, projects):
        mapping = dict([
            (str(p['id']), p['title'])
            for p in projects
        ])
        return mapping

    def _get_components(self, components):
        mapping = dict([
            (str(c['id']), c['name'])
            for c in components
        ])
        return mapping

    def _get_milestones(self, milestones):
        mapping = dict([
            ((str(m['project_id']), str(m['title'])), m['id'])
            for m in milestones
        ])
        return mapping

    def _get_custom_fields(self, custom_fields):
        mapping = dict([
            ((str(cf['project_id']), str(cf['id'])), cf['value'])
            for cf in custom_fields
        ])
        return mapping


class UnfuddleFetcher(UnfuddleMetadataFetcher):
    """
conditions-string:
A comma or vertical bar separated list of report criteria composed as
    "field-expr-value, field-expr-value | field-expr-value"

    "field" is one of the following: [number, summary, priority, status,
        resolution, milestone, component,  version, severity, reporter,
        assignee, created_at, updated_at, last_comment_at, due_on,
        field_1, field_2, field_3]
    "expr" is one of the following: [eq, neq, gt, lt, gteq, lteq]
    "value" is an appropriate value for the given field; "value" can also be
        "current" for fields that represent people.

    Note: The comma acts as the AND operator and the vertical bar as the OR
        operator
    Example: "assignee-eq-current,status-eq-closed|status-eq-resolved"
        translates into
        Assignee is the Current user AND (Status is Closed OR Status is
                                          Resolved)
    """
    PRIORITY_MAP = {
        '1': 'Lowest',
        '2': 'Low',
        '3': 'Normal',
        '4': 'High',
        '5': 'Highest',
    }
    BUG_PRODUCER_CLASS = UnfuddleBugProducer

    def __init__(self, *args, **kwargs):
        super(UnfuddleFetcher, self).__init__(*args, **kwargs)

    def api_url(self, project_id=None):
        # all projects
        api = '/api/v1/ticket_reports/dynamic.json'

        # particular project
        project_api = '/api/v1/projects/%s/ticket_reports/dynamic.json'

        if project_id:
            path = project_api % project_id
        else:
            path = api
        return str(make_path(self.tracker.get_url(), path))

    def check_if_failed(self, response):
        if response.status_code == 401:
            if response.cookies['authenticated'] == 'false':
                raise FetcherBadDataError(
                    "You don't have proper credentials for tracker {}"
                    .format(self.tracker.name))
        super(UnfuddleFetcher, self).check_if_failed(response)

    def fetch(self, url):
        rpc = RPC(url=url)
        return rpc

    def get_resolved_conditions(self):
        return 'status-eq-resolved'

    def get_unresolved_conditions(self):
        return 'status-neq-closed,status-neq-resolved'

    def get_user_conditions(self, all=False):
        if all:
            unfuddle_login_mapping = self.unfuddle_data['users']
            unfuddle_user_reverse_map = dict(
                (v, k) for k, v in unfuddle_login_mapping.iteritems()
            )
            user_ids = [
                unfuddle_user_reverse_map.get(username)
                for username in self.login_mapping.keys()
            ]
            user_conditions = [
                'assignee-eq-%s' % user_id
                for user_id in user_ids if user_id
            ]
            user_conditions = '|'.join(user_conditions)
        else:
            user_conditions = 'assignee-eq-current'
        return user_conditions

    def get_ticket_conditions(self, ticket_ids):
        ticket_conditions = [
            'number-eq-%s' % ticket_id
            for ticket_id in ticket_ids
        ]
        ticket_conditions = '|'.join(ticket_conditions)
        return ticket_conditions

    def fetch_user_tickets(self, resolved=False):
        url = self.api_url() + '?'
        if resolved:
            conditions_string = '%s,%s' % (
                self.get_user_conditions(),
                self.get_resolved_conditions(),
            )
        else:
            conditions_string = '%s,%s' % (
                self.get_user_conditions(),
                self.get_unresolved_conditions(),
            )
        full_url = serialize_url(url, conditions_string=conditions_string)
        rpc = self.fetch(full_url)
        self.consume(rpc)

    def fetch_all_tickets(self, resolved=False):
        url = self.api_url() + '?'
        if resolved:
            conditions_string = '%s,%s' % (
                self.get_resolved_conditions(),
                self.get_user_conditions(all=True),
            )
        else:
            conditions_string = '%s,%s' % (
                self.get_unresolved_conditions(),
                self.get_user_conditions(all=True),
            )

        full_url = serialize_url(url, conditions_string=conditions_string)
        rpc = self.fetch(full_url)
        self.consume(rpc)

    def fetch_bugs_for_query(self, ticket_ids=None, project_selector=None,
                             component_selector=None,
                             version=None, resolved=False):
        if not ticket_ids and not project_selector:
            raise TypeError(
                'fetch_bugs_for_query takes ticket_ids and project_selector'
            )

        url = self.api_url(project_selector) + '?'
        if resolved:
            conditions_string = self.get_resolved_conditions()
        else:
            conditions_string = self.get_unresolved_conditions()

        if ticket_ids:
            conditions_string += ',' + self.get_ticket_conditions(ticket_ids)

        full_url = serialize_url(url, conditions_string=conditions_string)
        rpc = self.fetch(full_url)
        self.consume(rpc)

    def fetch_scrum(self, sprint_name, project_id=None, component_id=None):
        projects_reversed = dict(
            (v, k) for k, v in self.unfuddle_data['projects'].iteritems()
        )
        _project_id = projects_reversed.get(project_id)
        if not _project_id:
            error = 'Could match project selector "%s" ' \
                    'to Unfuddle project names' % project_id
            raise FetcherBadDataError(error)

        url = self.api_url() + '?'
        milestone_id = self.unfuddle_data['milestones'].get(
            (str(_project_id), sprint_name)
        )
        if not milestone_id:
            error = 'Wrong sprint name'
            raise FetcherBadDataError(error)
        else:
            conditions_string = 'milestone-eq-%s' % milestone_id
            full_url = serialize_url(url, conditions_string=conditions_string)
            rpc = self.fetch(full_url)
            self.consume(rpc)

    def parse(self, data):
        """
        Available fields:
        u'field3_value_id', u'number', u'assignee_id', u'due_on',
        u'reporter_id', u'field2_value_id', u'resolution_description_format',
        u'id', u'description_format', u'priority', u'hours_estimate_initial',
        u'project_id', u'hours_estimate_current', u'status', u'description',
        u'field1_value_id', u'severity_id', u'version_id', u'updated_at',
        u'milestone_id', u'resolution_description', u'component_id',
        u'created_at', u'summary', u'resolution'
        """
        unfuddle_login_mapping = self.unfuddle_data['users']
        unfuddle_project_mapping = self.unfuddle_data['projects']
        unfuddle_component_mapping = self.unfuddle_data['components']

        try:
            jdata = json.loads(data)
        except ValueError as e:
            ERROR('Error while parsing unfuddle response:\n%s' % e)
            raise FetchException(e)

        if len(jdata['groups']) == 0:
            return []

        tickets = jdata['groups'][0]['tickets']
        result = []
        for ticket in tickets:
            bug_desc = dict(
                tracker=self.tracker,
                id=ticket['number'],
                desc=ticket['summary'],
                project_id=ticket['project_id'],
                reporter=unfuddle_login_mapping.get(
                    ticket['reporter_id'],
                    'unknown',
                ),
                owner=unfuddle_login_mapping.get(
                    ticket['assignee_id'],
                    'unknown',
                ),
                project_name=unfuddle_project_mapping.get(
                    str(ticket['project_id']),
                    'unknown',
                ),
                component_name=unfuddle_component_mapping.get(
                    str(ticket['component_id']),
                    'unknown',
                ),
                priority=self.PRIORITY_MAP[ticket['priority']],
                status=ticket['status'],
                opendate=dateutil.parser.parse(ticket['created_at']),
                changeddate=dateutil.parser.parse(ticket['updated_at']),
            )

            fields_no = self.unfuddle_data['whiteboard_field_numbers']
            field_no = fields_no.get(ticket['project_id'])
            if field_no:
                whiteboard_field_id = ticket.get('field%s_value_id' % field_no)
                key = str(ticket['project_id']), str(whiteboard_field_id)
                whiteboard = self.unfuddle_data['custom_fields'].get(key, '')
            else:
                whiteboard = ''
            bug_desc['whiteboard'] = whiteboard
            result.append(bug_desc)
        return result
