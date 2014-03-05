import datetime
import json
from calendar import timegm

from sqlalchemy import func

from intranet3.models import User, TimeEntry, Project
from intranet3 import helpers as h
from intranet3.models import DBSession
from .board import Board


def parse_whiteboard(wb):
    wb = wb.strip().replace('[', ' ').replace(']', ' ')
    if wb:
        return dict(i.split('=', 1) for i in wb.split() if '=' in i)
    return {}


def move_blocked_to_the_end(bugs):
    """Move blocked bugs to the end of the list"""
    return bugs


class SprintWrapper(object):
    def __init__(self, sprint, bugs, request):
        self.sprint = sprint
        self.request = request
        self.board = Board(sprint, bugs)

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

        for bug in self.board.bugs:
            if bug in self.board.completed_bugs:
                for date in tseries.iterkeys():
                    if date < bug.changeddate.date():
                        tseries[date] += bug.scrum.points
            else:
                for date in tseries.iterkeys():
                    tseries[date] += bug.scrum.points

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
            total_points=self.board.points,
        )

    def get_worked_hours(self):
        entries = DBSession.query(User, func.sum(TimeEntry.time), TimeEntry.ticket_id)\
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
        extra_tabs = DBSession.query(Project)\
                         .filter(Project.client_id == self.sprint.client_id)\
                         .first()\
                         .get_sprint_tabs
        return extra_tabs

    def get_info(self):
        entries, sum_worked_hours, sum_bugs_worked_hours = self.get_worked_hours()
        points_achieved = self.board.points_achieved
        points = self.board.points
        total_hours = sum_worked_hours
        total_bugs_hours = sum_bugs_worked_hours

        users = []
        if self.sprint.team_id:
            users = DBSession.query(User)\
                        .filter(User.id.in_(self.sprint.team.users))\
                        .filter(User.is_active==True)\
                        .order_by(User.name).all()
        result = dict(
            start=self.sprint.start.strftime('%Y-%m-%d'),
            end=self.sprint.end.strftime('%Y-%m-%d'),
            days_remaining=h.get_working_days(datetime.date.today(), self.sprint.end),
            total_bugs = len(self.board.bugs),
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
