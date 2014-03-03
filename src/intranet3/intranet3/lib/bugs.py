from __future__ import with_statement
from time import sleep, time

from intranet3.decorators import log_time
from intranet3.models import DBSession, TrackerCredentials, Tracker, Project, User
from intranet3.asyncfetchers import get_fetcher, FetcherBaseException, FetcherTimeout, FetcherBadDataError
from intranet3.log import INFO_LOG, WARN_LOG, ERROR_LOG
from intranet3.utils import flash
from intranet3 import memcache

LOG = INFO_LOG(__name__)
WARN = WARN_LOG(__name__)
ERROR = ERROR_LOG(__name__)

MAX_TIMEOUT = 50  # DON'T WAIT LONGER THAN DEFINED TIMEOUT

SCRUM_BUG_CACHE_KEY = 'sprint-%s'
SCRUM_BUG_CACHE_TIMEOUT = 3*60


class Bugs(object):

    def __init__(self, request, user=None):
        """
        If no user is provided,  we will fetch bugs using current user
        credentials
        """
        self.request = request
        self.user = user or request.user

    @log_time
    def _get_bugs(self, fetcher_callback, full_mapping=True):
        fetchers = []
        creds_q = DBSession.query(Tracker, TrackerCredentials, User)\
            .filter(Tracker.id == TrackerCredentials.tracker_id) \
            .filter(User.id == TrackerCredentials.user_id)\
            .filter(TrackerCredentials.user_id == self.user.id).all()

        for tracker, credentials, user in creds_q:
            fetcher = tracker.get_fetcher(
                credentials,
                self.user,
                full_mapping=full_mapping,
            )
            fetchers.append(fetcher)
            fetcher_callback(fetcher)  # initialize query
        bugs = []

        for fetcher in fetchers:
            try:
                fbugs = fetcher.get_result()
                bugs.extend(fbugs)
            except FetcherTimeout as e:
                flash(
                    'Fetchers for trackers %s timed-out' % fetcher.tracker.name,
                    klass='error',
                )
            except FetcherBadDataError as e:
                flash(e, klass='error')
            except FetcherBaseException as e:
                flash(
                    'Could not fetch bugs from tracker %s' % fetcher.tracker.name,
                    klass='error',
                )

        projects = {}
        for bug in bugs:
            projects[bug.project_id] = None
            # query for all project id's
        projects = dict((project.id, project) for project in Project.query.filter(Project.id.in_(projects.keys())))
        # now assign projects to bugs
        for bug in bugs:
            bug.project = projects.get(bug.project_id)
        return bugs

    def _get_credentials(self, tracker_id):
        creds = TrackerCredentials.query.filter(TrackerCredentials.user_id==self.user.id)\
                                        .filter(TrackerCredentials.tracker_id==tracker_id).first()
        return creds

    ## interface:

    def get_user(self, resolved=False):
        """
        Get user's bugs from all trackers
        """
        bugs = self._get_bugs(lambda fetcher: fetcher.fetch_user_tickets(resolved=resolved), full_mapping=False)
        bugs = self.add_time(bugs)
        return bugs

    def get_all(self, resolved=False):
        """
        Get all bugs from all trackers
        This number of bugs is limited by used user's credentials.
        """
        bugs = self._get_bugs(lambda fetcher: fetcher.fetch_all_tickets(resolved=resolved), full_mapping=True)
        bugs = self.add_time(bugs)
        return bugs

    def get_project(self, project, resolved=False, credentials=None):
        """
        Get bugs for given project
        """
        start = time()
        bugs = []
        tracker = project.tracker
        credentials = credentials or self._get_credentials(tracker.id)

        if not credentials:
            return []

        login_mapping = TrackerCredentials.get_logins_mapping(tracker)
        fetcher = get_fetcher(tracker, credentials, self.user, login_mapping)
        fetcher.fetch_bugs_for_query(*project.get_selector_tuple(), resolved=resolved)

        bugs = []

        try:
            for bug in fetcher.get_result():
                bug.project = project
                bugs.append(bug)
        except FetcherTimeout as e:
            flash(
                'Fetchers for trackers %s timed-out' % fetcher.tracker.name,
                klass='error',
            )
        except FetcherBadDataError as e:
            flash(e, klass='error')
        except FetcherBaseException as e:
            flash(
                'Could not fetch bugs from tracker %s' % fetcher.tracker.name,
                klass='error',
            )

        bugs = self.add_time(bugs)
        return bugs

    def get_sprint(self, sprint):
        project_ids = sprint.bugs_project_ids

        entries = DBSession.query(Project, Tracker, TrackerCredentials, User) \
                   .filter(Project.id.in_(project_ids)) \
                   .filter(Project.tracker_id==Tracker.id) \
                   .filter(TrackerCredentials.tracker_id==Project.tracker_id) \
                   .filter(TrackerCredentials.user_id==User.id)\
                   .filter(TrackerCredentials.user_id==self.user.id).all()

        fetchers = []
        for project, tracker, creds, user in entries:
            fetcher = tracker.get_fetcher(creds, user, full_mapping=True)
            fetcher.fetch_scrum(sprint.name, project.project_selector,
                                project.component_selector)
            fetchers.append(fetcher)
            if tracker.type in ('bugzilla', 'rockzilla', 'igozilla'):
                break

        start = time()
        bugs = []

        for fetcher in fetchers:
            try:
                fbugs = fetcher.get_result()
            except FetcherTimeout as e:
                flash(
                    'Fetchers for trackers %s timed-out' % fetcher.tracker.name,
                    klass='error',
                    )
                continue
            except FetcherBadDataError as e:
                flash(e, klass='error')
                continue
            except FetcherBaseException as e:
                flash(
                    'Could not fetch bugs from tracker %s' % fetcher.tracker.name,
                    klass='error',
                    )
                continue
            bugs.extend(fbugs)


        projects = [bug.project_id for bug in bugs]
        projects = dict((project.id, project) for project in Project.query.filter(Project.id.in_(projects)))

        # now assign projects to bugs
        for bug in bugs:
            bug.project = projects.get(bug.project_id)

        bugs = self.add_time(bugs, sprint=sprint)
        return bugs

    @classmethod
    def add_time(cls, orig_bugs, sprint=None):
        """
        @param orig_bugs: list of bugs
        Add times to bugs, can be used inside and outside the class.
        """
        bugs = dict(((bug.id, bug.project_id), bug) for bug in orig_bugs if bug.project)
        where_condition = '(t.ticket_id = :bug_id_%s AND t.project_id = :project_id_%s)'
        conditions = []
        params = {}
        i = 1
        for bug_id, project_id in bugs:
            conditions.append(where_condition % (i, i))
            params['bug_id_%s' % i] = bug_id
            params['project_id_%s' % i] = project_id
            i += 1
        if not conditions:
            return orig_bugs # short circuit to avoid useless (and incorrect) SQL query
        condition = ' OR '.join(conditions)
        sql = """
        SELECT t.ticket_id as "ticket_id", t.project_id as "project_id", SUM(t.time) as "time"
        FROM time_entry t
        WHERE t.deleted = FALSE AND (%s)
        GROUP BY t.ticket_id, t.project_id
        """ % (condition, )
        query = DBSession.query('ticket_id', 'project_id', 'time').from_statement(sql).params(**params)

        for bug_id, project_id, time in query:
            bug = bugs[(bug_id, project_id)]
            bug.time = time
            points = bug.scrum.points or 0.0
            velocity = ((points / time) * 8.0) if time else 0.0
            bug.scrum.velocity = velocity


        if sprint:
            params['sprint_start'] = sprint.start
            params['sprint_end'] = sprint.end
            sql = """
            SELECT t.ticket_id as "ticket_id", t.project_id as "project_id", SUM(t.time) as "time"
            FROM time_entry t
            WHERE t.deleted = FALSE AND (%s) AND t.date >= :sprint_start AND t.date <= :sprint_end
            GROUP BY t.ticket_id, t.project_id
            """ % (condition, )
            query = DBSession.query('ticket_id', 'project_id', 'time').from_statement(sql).params(**params)

            for bug in orig_bugs:
                bug.sprint_time = 0.0

            for bug_id, project_id, time in query:
                bugs[(bug_id, project_id)].sprint_time = time

        return orig_bugs
