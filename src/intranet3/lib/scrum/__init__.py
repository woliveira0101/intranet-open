import datetime
import json
import copy
from calendar import timegm

from sqlalchemy import func
from sqlalchemy.sql import or_, and_

from intranet3.models import User, TimeEntry, Project
from intranet3 import helpers as h


class BugUglyAdapter(object):
    """
    Temporary hack
    """

    def __init__(self, bug):
        self._bug = bug
        self._bug_tracker_type = bug.tracker.type # after saving to memcached

    def __getattr__(self, item):
        return getattr(self._bug, item)

    def is_closed(self):

        if self._bug.project.client_id == 20:
            return self._bug.get_status() == 'VERIFIED' and self._bug.get_resolution() == 'DEPLOYED'
        elif self._bug_tracker_type == 'pivotaltracker':
            return self._bug.status in ('delivered', 'accepted')
        else:
            return self._bug.get_status() == 'CLOSED' or self._bug.get_status() == 'VERIFIED'

    @property
    def points(self):
        try:
            return float(self.whiteboard.get('p', 0.0))
        except:
            return 0.0

    @property
    def velocity(self):
        points = self.points
        return (points / self.time * 8.0) if self.time else 0.0

    @classmethod
    def produce(cls, bugs):
        bugs = [BugUglyAdapter(bug) for bug in bugs]
        bugs_dict = dict([(bug.id, bug) for bug in bugs])

        # remove dependson and blocked bugs that are not in this sprint
        for bug in bugs:
            for dependon_bug in bug.dependson.keys():
                if dependon_bug not in bugs_dict or bug.dependson[dependon_bug]['resolved']:
                    del bug.dependson[dependon_bug]

            # when bug is closed it does block nothing
            if bug.is_closed():
                bug.blocked = {}

            for blocked_bug in bug.blocked.keys():
                if blocked_bug not in bugs_dict:
                    del bug.blocked[blocked_bug]

        # add bug reference to dependson and blocked dictionaries
        for bug in bugs:
            for dependon_bug in bug.dependson.keys():
                bug.dependson[dependon_bug]['bug'] = bugs_dict[dependon_bug]
            for blocked_bug in bug.blocked.keys():
                bug.blocked[blocked_bug]['bug'] = bugs_dict[blocked_bug]
        return bugs


def parse_whiteboard(wb):
    wb = wb.strip().replace('[', ' ').replace(']', ' ')
    if wb:
        return dict(i.split('=', 1) for i in wb.split() if '=' in i)
    return {}


def move_blocked_to_the_end(bugs):
    """Move blocked bugs to the end of the list"""
    blocked_bugs = [bug for bug in bugs if bug.is_blocked]
    bugs = [bug for bug in bugs if not bug.is_blocked]
    bugs.extend(blocked_bugs)
    return bugs


class SprintWrapper(object):
    def __init__(self, sprint, bugs, request):
        self.sprint = sprint
        self.bugs = BugUglyAdapter.produce([b for b in bugs if getattr(b, 'project')])
        self.request = request
        self.session = request.db_session

    def _date_to_js(self, date):
        """Return unix epoc timestamp in miliseconds (in UTC)"""
        return timegm(date.timetuple()) * 1000

    def _get_burndown(self):
        """Return a list of total point values per day of sprint"""
        today = datetime.date.today()
        sdate = self.sprint.start
        edate = self.sprint.end if self.sprint.end < today else today
        if sdate > today:
            return []
        tseries = dict([(cdate, 0) for cdate in h.dates_between(sdate, edate) ])

        for bug in self.bugs:
            if bug.is_closed() or bug.get_status() == 'RESOLVED':
                for date in tseries.iterkeys():
                    if date < bug.changeddate.date():
                        tseries[date] += bug.points
            else:
                for date in tseries.iterkeys():
                    tseries[date] += bug.points

        tseries = [ (self._date_to_js(v[0]), v[1]) for v in sorted(tseries.iteritems(), key=lambda x: x[0]) ]
        return tseries

    def _get_burndown_axis(self):
        """Return a list of epoch dates between sprint start and end
        inclusive"""
        return [self._date_to_js(cdate) for cdate in
                h.dates_between(self.sprint.start, self.sprint.end)]

    def get_burndown_data(self):
        return dict(
            burndown=self._get_burndown(),
            burndown_axis=self._get_burndown_axis(),
            total_points=self.get_points(),
        )

    def get_points_achieved(self):
        points = sum([ bug.points for bug in self.bugs if bug.is_closed()])
        return points

    def get_points(self):
        points = sum([ bug.points for bug in self.bugs ])
        return points

    def get_worked_hours(self):
        # DEPRECIATED:
        #bugs_ids = [(int(bug.project_id), bug.id) for bug in self.bugs]
        #if not self.bugs:
        #    return [], 0
        #
        #bug_ids_cond = or_(*[ and_(TimeEntry.project_id==p_id, TimeEntry.ticket_id==b_id)  for p_id, b_id in bugs_ids ])

        entries = self.session.query(User, func.sum(TimeEntry.time), TimeEntry.ticket_id)\
                              .filter(TimeEntry.user_id==User.id)\
                              .filter(TimeEntry.project_id==self.sprint.project_id) \
                              .filter(TimeEntry.added_ts>=self.sprint.start)\
                              .filter(TimeEntry.added_ts<=self.sprint.end)\
                              .filter(TimeEntry.deleted==False)\
                              .group_by(User, TimeEntry.ticket_id).all()

        entries = [ (user.name, round(time), ticket_id)
                    for user, time, ticket_id in entries ]
        entries = sorted(entries, key=lambda x: x[1], reverse=True)

        return (
            entries,
            sum([e[1] for e in entries]),
            sum([e[1] for e in entries if e[2] and not e[2].startswith('M')])
        )

    def get_tabs(self):
        extra_tabs = self.session.query(Project)\
                         .filter(Project.client_id == self.sprint.client_id)\
                         .first()\
                         .get_sprint_tabs
        return extra_tabs

    def get_board(self):
        todo = dict(bugs=dict(blocked=[], with_points=[], without_points=[]), points=0, empty=True)
        inprocess = dict(bugs=dict(blocked=[], with_points=[], without_points=[]), points=0, empty=True)
        toverify = dict(bugs=dict(blocked=[], with_points=[], without_points=[]), points=0, empty=True)
        completed = dict(bugs=dict(blocked=[], with_points=[], without_points=[]), points=0, empty=True)

        def append_bug(d, bug):
            if bug.is_blocked:
                d['bugs']['blocked'].append(bug)
            elif bug.points:
                d['bugs']['with_points'].append(bug)
            else:
                d['bugs']['without_points'].append(bug)
            d['empty'] = False;

        for bug in self.bugs:
            points = bug.points
            if bug.is_closed():
                append_bug(completed, bug)
                completed['points'] += points
            elif bug.get_status() == 'RESOLVED':
                append_bug(toverify, bug)
                toverify['points'] += points
            elif not bug.is_unassigned():
                append_bug(inprocess, bug)
                inprocess['points'] += points
            else:
                append_bug(todo, bug)
                todo['points'] += points

        return dict(
            bugs=self.bugs,
            todo=todo,
            inprocess=inprocess,
            toverify=toverify,
            completed=completed,
        )

    def get_info(self):
        entries, sum_worked_hours, sum_bugs_worked_hours = self.get_worked_hours()
        points_achieved = self.get_points_achieved()
        points = self.get_points()
        total_hours = sum_worked_hours
        total_bugs_hours = sum_bugs_worked_hours

        users = []
        if self.sprint.team_id:
            users = self.session.query(User)\
                        .filter(User.id.in_(self.sprint.team.users))\
                        .filter(User.is_active==True)\
                        .order_by(User.name).all()
        result = dict(
            start=self.sprint.start.strftime('%Y-%m-%d'),
            end=self.sprint.end.strftime('%Y-%m-%d'),
            days_remaining=h.get_working_days(datetime.date.today(), self.sprint.end),
            total_bugs = len(self.bugs),
            users=users,
        )
        self.sprint.commited_points = points
        self.sprint.achieved_points = points_achieved
        self.sprint.worked_hours = total_hours
        self.sprint.bugs_worked_hours = total_bugs_hours
        return result


def get_velocity_chart_data(sprints):
    velocity_chart = [
        (s.name,
         s.commited_points,
         s.achieved_points) for s in sprints
    ]

    if velocity_chart:
        velocity_chart.insert(0, (u'Sprint name', u'Commited', u'Completed'))
        return json.dumps(velocity_chart)
    else:
        return None
