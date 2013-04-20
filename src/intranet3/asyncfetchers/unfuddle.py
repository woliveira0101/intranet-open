import json
import datetime
import dateutil.parser
from functools import partial

from intranet3 import memcache
from intranet3.helpers import Converter, serialize_url, make_path
from intranet3.asyncfetchers.base import BaseFetcher, BasicAuthMixin, Bug
from intranet3.log import EXCEPTION_LOG, INFO_LOG
from intranet3.utils import flash

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)

class UnfuddleTrackerBug(Bug):

    def get_url(self, number=None):
        number = number if number else self.id
        url = make_path(self.tracker.url, '/a#/projects/%s/tickets/by_number/%s')
        url = url % (self.project_name, number)
        return url

    def is_unassigned(self):
        if self.owner.name == 'nobody':
            return True
        else:
            return False

    def get_status(self):
        return self.status.upper()


unfuddletracker_converter = Converter(
    id='id',
    desc='desc',
    reporter='reporter',
    owner='owner',
    status='status',
    resolution=lambda d: '',
    project_name='project_name',
    opendate='opendate',
    changeddate='changeddate',
    priority='priority',
    severity='severity',
    component_name='component',
    deadline='deadline',
    whiteboard='whiteboard',
)


class UnfuddleUserFetcher(BasicAuthMixin, BaseFetcher):
    """
    Unfuddle returns user_id insted of username so
    we have to create new login mapping by fetching all users from unfuddle
    and then use it in self.parse
    """
    unfuddle_login_mapping = None
    UNFUDDLE_LOGIN_MAPPING_KEY = 'unfuddle_login_mapping'
    UNFUDDLE_LOGIN_MAPPING_TIMEOUT = 60*3
    people_api = '/api/v1/people.json'

    def get_users(self, callback):
        if not self.unfuddle_login_mapping:
            login_mapping = memcache.get(self.UNFUDDLE_LOGIN_MAPPING_KEY)
            if not login_mapping:
                self.fetch_users(callback)
                return
            else:
                self.unfuddle_login_mapping = login_mapping
        callback()

    def fetch_users(self, callback):
        headers = self.get_headers()
        url = self.tracker.url + self.people_api
        url = str(url)
        self.request(
            url,
            headers,
            partial(self.responded, on_success=partial(self.parse_users, callback)),
        )

    def parse_users(self, callback, data):
        jdata = json.loads(data)
        login_mapping = dict([ ( user['id'], user['username'] ) for user in jdata])
        login_mapping[None] = 'nobody'

        self.unfuddle_login_mapping = login_mapping
        memcache.set(self.UNFUDDLE_LOGIN_MAPPING_KEY, login_mapping, timeout=self.UNFUDDLE_LOGIN_MAPPING_TIMEOUT)
        callback()


class UnfuddleFetcher(UnfuddleUserFetcher):
    """
conditions-string:
A comma or vertical bar separated list of report criteria composed as
      "field-expr-value, field-expr-value | field-expr-value"

      "field" is one of the following: [number, summary, priority, status, resolution, milestone, component,  version,
                                        severity, reporter, assignee, created_at, updated_at, last_comment_at, due_on,
                                        field_1, field_2, field_3]
      "expr" is one of the following: [eq, neq, gt, lt, gteq, lteq]
      "value" is an appropriate value for the given field; "value" can also be "current" for fields that represent people.

    Note: The comma acts as the AND operator and the vertical bar as the OR operator
    Example: "assignee-eq-current,status-eq-closed|status-eq-resolved,milestone-eq-34584"
               translates into
             Assignee is the Current user AND (Status is Closed OR Status is Resolved) AND Milestone is 34584
    """
    PRIORITY_MAP = {
        '1': 'Lowest',
        '2': 'Low',
        '3': 'Normal',
        '4': 'High',
        '5': 'Highest',
    }
    bug_class = UnfuddleTrackerBug
    get_converter = lambda self: unfuddletracker_converter

    def __init__(self, *args, **kwargs):
        self._milestones = {}
        self._custom_fields = {}
        super(UnfuddleFetcher, self).__init__(*args, **kwargs)

    def api_url(self, project_id=None):
        api = '/api/v1/ticket_reports/dynamic.json' # all projects
        project_api = '/api/v1/projects/%s/ticket_reports/dynamic.json' # particular project
        if project_id:
            path = project_api % project_id
        else:
            path = api
        return str(make_path(self.tracker.url, path))

    def fetch(self, url, callback=None):
        if not self.unfuddle_login_mapping:
            self_callback = partial(self.fetch, url)
            self.get_users(self_callback)
        else:
            headers = self.get_headers()
            self.request(url, headers, self.responded)

    def get_resolved_conditions(self):
        return 'status-eq-resolved'

    def get_unresolved_conditions(self):
        return 'status-neq-closed,status-neq-resolved'

    def get_user_conditions(self, all=False):
        if all:
            unfuddle_user_reverse_map = dict((v,k) for k, v in self.unfuddle_login_mapping.iteritems())
            user_ids = [ unfuddle_user_reverse_map.get(username) for username in self.login_mapping.keys()]
            user_conditions = [ 'assignee-eq-%s' % user_id for user_id in user_ids if user_id]
            user_conditions = '|'.join(user_conditions)
        else:
            user_conditions = 'assignee-eq-current'
        return user_conditions

    def get_ticket_conditions(self, ticket_ids):
        ticket_conditions = [ 'number-eq-%s' % ticket_id for ticket_id in ticket_ids ]
        ticket_conditions = '|'.join(ticket_conditions)
        return ticket_conditions

    def fetch_user_tickets(self):
        url = self.api_url() + '?'
        conditions_string = '%s,%s' % (self.get_user_conditions(), self.get_unresolved_conditions())
        full_url = serialize_url(url, conditions_string=conditions_string)
        self.fetch(full_url)

    def fetch_user_resolved_tickets(self):
        url = self.api_url() + '?'
        conditions_string = '%s,%s' % (self.get_user_conditions(), self.get_resolved_conditions())
        full_url = serialize_url(url, conditions_string=conditions_string)
        self.fetch(full_url)

    def fetch_all_tickets(self):
        if not self.unfuddle_login_mapping:
            self.get_users(self.fetch_all_tickets)
        else:
            url = self.api_url() + '?'
            conditions_string = '%s,%s' % (self.get_unresolved_conditions(), self.get_user_conditions(all=True))
            full_url = serialize_url(url, conditions_string=conditions_string)
            self.fetch(full_url)

    def fetch_all_resolved_tickets(self):
        if not self.unfuddle_login_mapping:
            self.get_users(self.fetch_all_resolved_tickets)
        else:
            url = self.api_url() + '?'
            conditions_string = '%s,%s' % (self.get_resolved_conditions(), self.get_user_conditions(all=True))
            full_url = serialize_url(url, conditions_string=conditions_string)
            self.fetch(full_url)

    def fetch_bugs_for_query(self, ticket_ids, project_selector, component_selector, version):
        url = self.api_url(project_selector) + '?'
        conditions_string = self.get_unresolved_conditions()
        if ticket_ids:
            conditions_string += ',' + self.get_ticket_conditions(ticket_ids)

        full_url = serialize_url(url, conditions_string=conditions_string)
        self.fetch(full_url)

    def fetch_resolved_bugs_for_query(self, ticket_ids, project_selector, component_selector, version):
        url = self.api_url(project_selector) + '?'
        conditions_string = self.get_resolved_conditions()
        if ticket_ids:
            conditions_string += ',' + self.get_ticket_conditions(ticket_ids)

        full_url = serialize_url(url, conditions_string=conditions_string)
        self.fetch(full_url)

    def fetch_scrum(self, sprint_name, project_id=None):
        if not self._custom_fields:
            url = '/api/v1/projects/%s/custom_field_values.json' % project_id
            url = str(make_path(self.tracker.url, url))
            self.request(
                url,
                self.get_headers(),
                partial(self.responded, on_success=partial(self.parse_custom_fields, partial(self.fetch_scrum, sprint_name, project_id))),
            )
        elif not self._milestones:
            url = '/api/v1/milestones.json'
            url = str(make_path(self.tracker.url, url))
            self.request(
                url,
                self.get_headers(),
                partial(self.responded, on_success=partial(self.parse_milestones, partial(self.fetch_scrum, sprint_name, project_id))),
            )
        else:
            url = self.api_url() + '?'
            milestone_id = self._milestones.get(sprint_name)
            if not milestone_id:
                flash('Wrong sprint name')
                self.fail('Wrong sprint name')
            else:
                conditions_string = 'milestone-eq-%s' % self._milestones[sprint_name]
                full_url = serialize_url(url, conditions_string=conditions_string)
                self.fetch(full_url)

    def parse_custom_fields(self, callback, data):
        jdata = json.loads(data)
        for field in jdata:
            if field['field_number'] == 3:
                self._custom_fields[field['id']] = field['value']
        callback()

    def parse_milestones(self, callback, data):
        jdata = json.loads(data)
        for milestone in jdata:
            self._milestones[milestone['title']] = milestone['id']
        callback()

    def parse(self, data):
        """
        Available fields:
        u'field3_value_id', u'number', u'assignee_id', u'due_on', u'reporter_id', u'field2_value_id',
        u'resolution_description_format', u'id', u'description_format', u'priority', u'hours_estimate_initial',
        u'project_id', u'hours_estimate_current', u'status', u'description', u'field1_value_id', u'severity_id',
        u'version_id', u'updated_at', u'milestone_id', u'resolution_description', u'component_id', u'created_at',
        u'summary', u'resolution'
        """
        jdata = json.loads(data)
        if len(jdata['groups']) ==0:
            return

        tickets = jdata['groups'][0]['tickets']
        converter = self.get_converter()
        for ticket in tickets:
            bug_desc = dict(
                tracker=self.tracker,
                id=ticket['number'],
                desc=ticket['summary'],
                reporter=self.unfuddle_login_mapping.get(ticket['reporter_id'], 'unknown'),
                owner=self.unfuddle_login_mapping.get(ticket['assignee_id'], 'unknown'),
                status=ticket['status'],
                priority=self.PRIORITY_MAP[ticket['priority']],
                project_name=str(ticket['project_id']),
                opendate=dateutil.parser.parse(ticket['created_at']),
                changeddate=dateutil.parser.parse(ticket['updated_at']),
            )
            whiteboard_field_id = ticket['field3_value_id']
            if self._custom_fields and whiteboard_field_id:
                whiteboard = self._custom_fields[whiteboard_field_id]
                bug_desc['whiteboard'] = whiteboard

            yield self.bug_class(
                tracker=self.tracker,
                **converter(bug_desc)
            )
