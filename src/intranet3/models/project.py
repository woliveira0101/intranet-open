import re

from pprint import pformat
from sqlalchemy import Column, ForeignKey, orm
from sqlalchemy.types import String, Integer, Boolean, Text
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy import event, func
from sqlalchemy.util.langhelpers import symbol

from intranet3 import memcache
from intranet3.models import Base, DBSession, User
from intranet3.log import WARN_LOG, INFO_LOG, DEBUG_LOG


LOG = INFO_LOG(__name__)
DEBUG = DEBUG_LOG(__name__)
WARN = WARN_LOG(__name__)

SELECTOR_CACHE_KEY = 'SELECTORS_FOR_TRACKER_%s'

STATUS = [
    ('1', 'Initialization'),
    ('2', 'Analysis'),
    ('3', 'Conception'),
    ('4', 'Realization'),
    ('5', 'Support'),
    ('6', 'Closed'),
]


def bugzilla_bug_list(tracker_url, bug_ids, project_selector=None):
    query = '&'.join(['bug_id=%s' % bug_id for bug_id in bug_ids])
    return tracker_url + '/buglist.cgi?%s' % query


def unfuddle_bug_list(tracker_url, bug_ids, project_selector=None):

    suffix = '/a#/projects/%s/ticket_reports/dynamic?conditions_string=%s'
    query = '|'.join(['number-eq-%s' % bug_id for bug_id in bug_ids])
    return tracker_url + (suffix % (project_selector, query))


class Project(Base):
    __tablename__ = 'project'

    BUG_LIST_URL_CONTRUCTORS = {
        'bugzilla': bugzilla_bug_list,
        'rockzilla': bugzilla_bug_list,
        'igozilla': bugzilla_bug_list,
        'trac': lambda *args: '#',
        'cookie_trac': lambda *args: '#',
        'bitbucket': lambda *args: '#',
        'pivotaltracker': lambda *args: '#',
        'unfuddle': unfuddle_bug_list,
        'github': lambda *args: '#'
    }

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    coordinator_id = Column(Integer, ForeignKey('user.id'), nullable=True, index=True)
    client_id = Column(Integer, ForeignKey('client.id'), nullable=False, index=True)
    tracker_id = Column(Integer, ForeignKey('tracker.id'), nullable=False, index=True)

    turn_off_selectors = Column(Boolean, nullable=False, default=False)
    project_selector = Column(String, nullable=True)
    component_selector = Column(String, nullable=True)
    ticket_id_selector = Column(String, nullable=True)
    version_selector = Column(String, nullable=True)

    active = Column(Boolean, nullable=False)

    time_entries = orm.relationship('TimeEntry', backref='project', lazy='dynamic')
    sprints = orm.relationship('Sprint', backref='project', lazy='dynamic')

    google_card = Column(String, nullable=True)
    google_wiki = Column(String, nullable=True)
    status = Column(Integer, nullable=True)
    mailing_url = Column(String, nullable=True)

    working_agreement = Column(Text, nullable=False, default='')
    definition_of_done = Column(Text, nullable=False, default='')
    definition_of_ready = Column(Text, nullable=False, default='')
    continuous_integration_url = Column(String, nullable=False, default='')
    backlog_url = Column(String, nullable=False, default='')

    sprint_tabs = Column(Text, nullable=False, default='')

    __table_args__ = (UniqueConstraint('name', 'client_id', name='project_name_client_id_unique'), {})

    @property
    def get_sprint_tabs(self):
        return re.findall('(.+)\|(.+)(?:\n|$)', self.sprint_tabs)

    def format_selector(self):
        if self.turn_off_selectors:
            return u'Turned off'
        if self.ticket_id_selector:
            return u'Tickets: %s' % (self.ticket_id_selector, )
        else:
            return u'%s / %s / %s' % (
                self.project_selector or u'*',
                self.component_selector or u'*',
                self.version_selector or u'*',
            )

    def get_selector_tuple(self):
        """
        Returns selector tuple
        ([ticket_ids], project_selector, component_selector)
        """
        ticket_ids = [
            int(v.strip()) for v in self.ticket_id_selector.split(',')
        ] if self.ticket_id_selector else []

        components = [
            v.strip() for v in self.component_selector.split(',')
        ] if self.component_selector else []

        versions = [
            v.strip() for v in self.version_selector.split(',')
        ] if self.version_selector else []

        return (
            ticket_ids,
            self.project_selector,
            components,
            versions,
        )

    def get_new_bug_url(self):
        """
        Returns url for create new bug in project
        """
        component_selector = self.component_selector if self.component_selector is not None and not self.component_selector.count(',') else None
        return self.tracker.get_new_bug_url(self.project_selector, component_selector)

    def get_bug_list_url(self, bug_ids):
        constructor = self.BUG_LIST_URL_CONTRUCTORS[self.tracker.type]
        return constructor(self.tracker.url, bug_ids, self.project_selector)

    @property
    def status_name(self):
        if self.status and len(STATUS) >= self.status:
            return STATUS[self.status-1][1]
        return None

    @property
    def coordinator(self):
        if self.coordinator_id is not None:
            return User.query.filter(User.id==self.coordinator_id).one()
        else:
            return self.client.coordinator


class SelectorMapping(object):
    """ Simple storage for cached project selectors """

    def __init__(self, tracker):
        """
        Creates a selector mapping for given tracker
        None -> project_id
        project_name -> project_id
        (project_name, component_name) -> project_id
        """

        self.tracker = tracker
        self.by_ticket_id = {}

        self.default = None
        self.by_project = {}            # key: project_name
        self.by_component = {}          # key: project_name, component_name
        self.by_version = {}            # key: project_name, version
        self.by_component_version = {}  # key: project_name, component_name, version

        cache_key = SELECTOR_CACHE_KEY % tracker.id
        mapping = memcache.get(cache_key)
        if mapping:
            self.clone(mapping)
            return

        projects = Project.query.filter(Project.tracker_id == tracker.id) \
                                .filter(Project.turn_off_selectors == False) \
                                .filter(Project.active == True)
        self.projects = dict([(project.id, project.name) for project in projects])

        for project in projects:
            self._create_for_project(project)

        memcache.set(cache_key, self)
        DEBUG('Created selector mapping for tracker %s: %s, %s' % (
            tracker.id, pformat(self.by_ticket_id), pformat(self.by_component))
        )

    def clone(self, mapping):
        self.default = mapping.default
        self.by_project = mapping.by_project
        self.by_component = mapping.by_component
        self.by_version = mapping.by_version
        self.by_component_version = mapping.by_component_version

    def _check_ticket_id_existance(self, ticket_id):
        if ticket_id in self.by_ticket_id:
            WARN(u'Overriding ticket ID for tracker from %s to %s' % (
                self.by_ticket_id[ticket_id], ticket_id))

    def _check_project_component_existance(self, project_component, project):
        """
        Warn if we override a project
        """
        if project_component is None:
            if None in self.by_component:
                WARN(u'Overriding default project for tracker [%s] from [%s] to [%s]' % (
                    self.tracker.name,
                    self.projects[self.by_component[None]],
                    project.name
                ))
        elif isinstance(project_component, (str, unicode)):
            project_name = project_component
            if project_name in self.by_component:
                WARN(u'Overriding project [%s] for tracker [%s] from [%s] to [%s]' % (
                    project_name,
                    self.tracker.name,
                    self.projects[self.by_component[project_name]],
                    project.name
                ))
        else:
            project_name, component_name = project_component
            if (project_name, component_name) in self.by_component:
                WARN(u'Overriding project [%s] and component [%s] for tracker [%s] from [%s] to [%s]' % (
                    project_name,
                    component_name,
                    self.tracker.name,
                    self.projects[self.by_component[(project_name, component_name)]],
                    project.name
                ))

    def _create_for_project(self, project):
        ticket_ids, project_name, component_names, versions = project.get_selector_tuple()

        if ticket_ids:
            for ticket_id in ticket_ids:
                self._check_ticket_id_existance(ticket_id)
                self.by_ticket_id[ticket_id] = project.id

        # brak
        # tylko projekt
        # projekt + komponent
        # projekt + wersja
        # projekt + komponent + wersja

        if not project_name:
            # brak
            self._check_project_component_existance(None, project)
            self.default = project.id
        elif not component_names:
            if versions:
                # projekt + wersja
                for version in versions:
                    self.by_version[(project_name, version)] = project.id
            else:
                # tylko projekt
                self._check_project_component_existance(project_name, project)
                self.by_project[project_name] = project.id
        elif not versions:
            # projekt + komponent
            for component_name in component_names:
                self._check_project_component_existance((project_name, component_name), project)
                self.by_component[(project_name, component_name)] = project.id
        else:
            # projekt + komponent + wersja
            for component_name in component_names:
                for version in versions:
                    self.by_component_version[(project_name, component_name, version)] = project.id

    def match(self, id_, project, component, version=None):
        if id_ in self.by_ticket_id:
            return self.by_ticket_id[id_]

        project_id = self.by_component_version.get((project, component, version))
        if project_id:
            return project_id

        project_id = self.by_component.get((project, component))
        if project_id:
            return project_id

        project_id = self.by_version.get((project, version))
        if project_id:
            return project_id

        project_id = self.by_project.get(project)
        if project_id:
            return project_id

        if self.default:
            return self.default

        WARN(u'map_to_project: Mapping to project/component/tracker %s/%s/%s failed' % (project, component, self.tracker.name))

    @staticmethod
    def invalidate_for(tracker_id):
        memcache.delete(SELECTOR_CACHE_KEY % tracker_id)
        DEBUG(u'Invalidated selector mapping cache for tracker %s' % (tracker_id, ))

    @classmethod
    def recalculate_coordinators(cls):
        pass


@event.listens_for(Project.coordinator_id, 'set')
def after_set(target, value, oldvalue, initiator):
    if value != oldvalue:
        target.old_coordinator = oldvalue


def add_coordinator(session, user_id):
    user = session.query(User).filter(User.id==user_id).first()
    if 'coordinator' not in user.groups:
        groups = user.groups[:]
        groups.append('coordinator')
        user.groups = groups

def remove_coordinator(session, user_id):
    from intranet3.models import Client
    user, pc, cc = session.query(User, func.count(Project.id), func.count(Client.id))\
                         .filter(User.id==user_id)\
                         .outerjoin(Project, Project.coordinator_id==User.id)\
                         .outerjoin(Client, Client.coordinator_id==User.id)\
                         .group_by(User.id).first()
    if (pc+cc) <= 1:
        groups = user.groups[:]
        if 'coordinator' in groups:
            groups.remove('coordinator')
            user.groups = groups


@event.listens_for(DBSession, 'before_flush')
def before_flush(session, *args):
    from intranet3.models import Client
    project_or_client = None
    for obj in session:
        if isinstance(obj, (Project, Client)) and hasattr(obj, 'old_coordinator'):
            project_or_client = obj

    if not project_or_client:
        return

    oldc = project_or_client.old_coordinator
    if oldc and oldc != symbol('NO_VALUE'):
        remove_coordinator(session, project_or_client.old_coordinator)

    if project_or_client.coordinator_id:
        add_coordinator(session, project_or_client.coordinator_id)
