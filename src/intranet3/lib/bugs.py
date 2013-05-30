from __future__ import with_statement
from time import sleep, time

from intranet3.decorators import log_time
from intranet3.models import DBSession, TrackerCredentials, Tracker, Project
from intranet3.asyncfetchers import get_fetcher
from intranet3.log import INFO_LOG, WARN_LOG, ERROR_LOG
from intranet3.utils import flash
from intranet3 import memcache

LOG = INFO_LOG(__name__)
WARN = WARN_LOG(__name__)
ERROR = ERROR_LOG(__name__)

MAX_TIMEOUT = 20 # DON'T WAIT LONGER THAN DEFINED TIMEOUT

SCRUM_BUG_CACHE_KEY = 'sprint-%s'
SCRUM_BUG_CACHE_TIMEOUT = 3*60


class Bugs(object):

    def __init__(self, request, user=None):
        """
        If no user is provided,  we will fetch bugs using current user credentials
        """
        self.request = request
        self.user = user or request.user

    @log_time
    def _get_bugs(self, fetcher_callback, full_mapping=True):
        start = time()
        fetchers = []
        creds_q = DBSession.query(Tracker, TrackerCredentials)\
                           .filter(Tracker.id==TrackerCredentials.tracker_id)\
                           .filter(TrackerCredentials.user_id==self.user.id)
        for tracker, credentials in creds_q:
            if full_mapping:
                mapping = TrackerCredentials.get_logins_mapping(tracker)
            else:
                mapping = {credentials.login.lower(): self.user}
            fetcher = get_fetcher(tracker, credentials, mapping)
            fetchers.append(fetcher)
            fetcher_callback(fetcher) # initialize query
        bugs = []
        while fetchers:
            for i, fetcher in enumerate(fetchers):
                if fetcher.isReady():
                    fetchers.pop(i)
                    if fetcher.error:
                        WARN(u"Could not fetch bugs from tracker %s: %s" % (fetcher.tracker.name, fetcher.error))
                        flash(u"Could not fetch bugs from tracker %s" % (fetcher.tracker.name, ))
                    else:
                        for bug in fetcher:
                            bugs.append(bug)
                    break
            else:
                # no fetcher is yet ready, give them time
                if time() - start > MAX_TIMEOUT:
                    WARN(u"Fetchers for trackers %s timed-out" % (u', '.join(fetcher.tracker.name for fetcher in fetchers)))
                    for fetcher in fetchers:
                        pass
                        flash(u"Getting bugs from tracker %s timed out" % (fetcher.tracker.name, ))
                    fetchers = []
                else:
                    sleep(0.1)
                    # all bugs were fetched, time to resolve their projects
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
        if resolved:
            bugs = self._get_bugs(lambda fetcher: fetcher.fetch_user_resolved_tickets(), full_mapping=False)
        else:
            bugs = self._get_bugs(lambda fetcher: fetcher.fetch_user_tickets(), full_mapping=False)

        bugs = self.add_time(bugs)
        return bugs

    def get_all(self, resolved=False):
        """
        Get all bugs from all trackers
        This number of bugs is limited by used user's credentials.
        """
        if resolved:
            bugs = self._get_bugs(lambda fetcher: fetcher.fetch_all_resolved_tickets(), full_mapping=True)
        else:
            bugs = self._get_bugs(lambda fetcher: fetcher.fetch_all_tickets(), full_mapping=True)

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
        fetcher = get_fetcher(tracker, credentials, login_mapping)
        (fetcher.fetch_resolved_bugs_for_query if resolved else fetcher.fetch_bugs_for_query)(*project.get_selector_tuple())

        while True:
            if fetcher.isReady():
                if fetcher.error:
                    WARN(u"Could not fetch bugs from tracker %s: %s" % (tracker.name, fetcher.error))
                    flash(u"Could not fetch bugs from tracker %s" % (tracker.name, ))
                else:
                    for bug in fetcher:
                        bug.project = project
                        bugs.append(bug)
                break
            elif time() - start > MAX_TIMEOUT:
                WARN(u"Fetchers for tracker %s timed-out" % (tracker.name, ))
                flash(u"Getting bugs from tracker %s timed out" % (tracker.name, ))
            else:
                sleep(0.1)

        bugs = self.add_time(bugs)
        return bugs

    def get_sprint(self, sprint):
        bugs = memcache.get(SCRUM_BUG_CACHE_KEY % sprint.id)
        if bugs:
            return bugs
        query = self.request.db_session.query
        tracker, creds = query(Tracker, TrackerCredentials)\
                            .filter(TrackerCredentials.tracker_id==sprint.project.tracker_id)\
                            .filter(TrackerCredentials.tracker_id==Tracker.id)\
                            .filter(TrackerCredentials.user_id==self.user.id).one()
        fetcher = get_fetcher(tracker, creds, tracker.logins_mapping)
        fetcher.fetch_scrum(sprint.name, sprint.project.project_selector)
        start = time()
        bugs = []
        while True:
            if fetcher.isReady():
                if fetcher.error:
                    ERROR(u"Fetcher for tracker %s failed with %r" % (tracker.name, fetcher.error))
                    break
                bugs = [ bug for bug in fetcher ]
                break
            else: # fetcher is not ready yet
                if time() - start > MAX_TIMEOUT:
                    ERROR(u'Request timed-out')
                    break
                else:
                    sleep(0.1)

        projects = {}
        for bug in bugs:
            projects[bug.project_id] = None
            # query for all project id's
        projects = dict((project.id, project) for project in Project.query.filter(Project.id.in_(projects.keys())))

        # now assign projects to bugs
        for bug in bugs:
            bug.project = projects.get(bug.project_id)

        bugs = self.add_time(bugs, sprint=sprint)
        memcache.set(SCRUM_BUG_CACHE_KEY % sprint.id, bugs, SCRUM_BUG_CACHE_TIMEOUT)
        return bugs

    def get_sprint(self, sprint):
        query = self.request.db_session.query

        # backward compatibility
        if not hasattr(sprint, 'project_ids'):
            sprint.project_ids = [sprint.project_id]

        entries = query(Project, Tracker, TrackerCredentials) \
                   .filter(Project.id.in_(sprint.project_ids)) \
                   .filter(Project.tracker_id==Tracker.id) \
                   .filter(TrackerCredentials.tracker_id==Project.tracker_id) \
                   .filter(TrackerCredentials.user_id==self.user.id).all()

        fetchers = [
            get_fetcher(tracker, creds, tracker.logins_mapping)
            for project, tracker, creds in entries
        ]
        for (project, tracker, creds), fetcher in zip(entries, fetchers):
            # TODO: optimize, group projects with the same tracker
            fetcher.fetch_scrum(sprint.name, project.project_selector)

        start = time()
        bugs = []
        while fetchers:
            for i, fetcher in enumerate(fetchers):
                if fetcher.isReady():
                    fetchers.pop(i)
                    if fetcher.error:
                        WARN(u"Could not fetch bugs from tracker %s: %s" % (fetcher.tracker.name, fetcher.error))
                        flash(u"Could not fetch bugs from tracker %s" % (fetcher.tracker.name, ))
                    else:
                        for bug in fetcher:
                            bugs.append(bug)
                    break
            else:
                # no fetcher is yet ready, give them time
                if time() - start > MAX_TIMEOUT:
                    WARN(u"Fetchers for trackers %s timed-out" % (u', '.join(fetcher.tracker.name for fetcher in fetchers)))
                    for fetcher in fetchers:
                        pass
                        flash(u"Getting bugs from tracker %s timed out" % (fetcher.tracker.name, ))
                    fetchers = []
                else:
                    sleep(0.1)
                    # all bugs were fetched, time to resolve their projects

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
            bugs[(bug_id, project_id)].time = time

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

            for bug in bugs.itervalues():
                bug.sprint_time = 0.0

            for bug_id, project_id, time in query:
                bugs[(bug_id, project_id)].sprint_time = time

        return orig_bugs
