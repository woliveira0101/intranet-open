# coding: utf-8
import calendar
import datetime

import colander
import iso8601

from pyramid.httpexceptions import HTTPBadRequest, HTTPCreated, HTTPForbidden, HTTPNotFound, HTTPOk, HTTPNoContent
from pyramid.view import view_config

from intranet3.forms.times import time_filter
from intranet3.helpers import previous_day, next_day, format_time
from intranet3.lib.bugs import Bugs
from intranet3.lib.times import user_can_modify_timeentry
from intranet3.models import User, Project, TimeEntry, Tracker
from intranet3.utils.views import ApiView
from intranet3.views.times import GetTimeEntriesMixin

from intranet3.schemas.times import AddEntrySchema, EditEntrySchema


class TimeCollection(GetTimeEntriesMixin, ApiView):

    def _entries_serializer(self, objs):
        l = []
        for tracker, entry in objs:
            entry_dict = entry.to_dict()
            # Add Tracker url
            entry_dict.update({
                'tracker_url': tracker.get_bug_url(entry.ticket_id),
            })
            l.append(entry_dict)
        return l

    def protect(self):
        user, date = self._get_params()
        is_same_user = user.id == self.request.user.id

        self.v['user'] = user
        self.v['date'] = date

        if self.request.has_perm('admin'):
            return

        if self.request.method == "POST":
            if not is_same_user or not user_can_modify_timeentry(self.request.user, date):
                raise HTTPForbidden()

        if self.request.method == "GET":
            if user.freelancer and not is_same_user:
                raise HTTPForbidden()

    def _get_params(self):
        date_str = self.request.GET.get('date')
        if date_str is not None:
            try:
                date = iso8601.parse_date(date_str).date()
            except iso8601.ParseError:
                raise HTTPBadRequest("Accepted date format ISO-8601: YYYY-MM-DD/YYYMMDD")
        else:
            date = datetime.date.today()

        try:
            user_id = int(self.request.GET.get('user_id', self.request.user.id))
        except ValueError:
            raise HTTPBadRequest("Wrong User ID")

        user = User.query.get(user_id)

        return user, date

    def get(self):
        user, date = self.v['user'], self.v['date']

        entries = self._get_time_entries(date, user.id)

        return {
            'entries': self._entries_serializer(entries)
        }

    def post(self):
        user, date = self.v['user'], self.v['date']

        try:
            schema = AddEntrySchema()
            data = schema.deserialize(self.request.POST)
        except colander.Invalid as e:
            return HTTPBadRequest(e.asdict())

        project_id = data.get('project_id')
        project = Project.query.get(project_id)
        if not project:
            raise HTTPBadRequest("Project is required")

        time = TimeEntry(
            date = date,
            user_id = user.id,
            time = data.get('time'),
            description = data.get('description'),
            ticket_id = data.get('ticket_id'),
            project_id = project_id if project_id else None,
            timer_ts = datetime.datetime.now() if data.get('timer') else None,
            frozen = bool(data.get('start_timer'))
        )
        self.session.add(time)

        return HTTPCreated('OK')


class Time(ApiView):

    def protect(self):
        '''
            User can edit `TimeEntry` only during current month
        '''
        timeentry_id = self.request.matchdict.get('id')
        timeentry = TimeEntry.query.get(timeentry_id)

        if timeentry is None:
            raise HTTPNotFound("Not Found")

        is_same_user = timeentry.user_id == self.request.user.id
        self.v['timeentry'] = timeentry

        if self.request.has_perm('admin'):
            return

        if self.request.method in ("PUT", "DELETE"):
            if not user_can_modify_timeentry(self.request.user, timeentry.date):
                raise HTTPForbidden()
            elif timeentry.deleted:
                raise HTTPBadRequest()
            elif not is_same_user:
                raise HTTPBadRequest()

        if self.request.method == "GET":
            if self.request.user.freelancer and not is_same_user:
                raise HTTPForbidden()

    def get(self):
        timeentry = self.v['timeentry']

        entry = timeentry.to_dict()
        # Add Tracker URL if project is not None
        if timeentry.project:
            tracker = Tracker.query.get(timeentry.project.tracker_id)
            entry.update({
                    'tracker_url': tracker.get_bug_url(timeentry.ticket_id),
            })

        return entry

    def put(self):
        timeentry = self.v['timeentry']
        today = datetime.date.today()

        try:
            schema = EditEntrySchema()
            data = schema.deserialize(self.request.POST)
        except colander.Invalid as e:
            return HTTPBadRequest(e.asdict())

        if timeentry.project_id != data.get('project_id') and today > timeentry.date:
            timeentry.deleted = True
            timeentry.modified_ts = datetime.datetime.now() 

            time = TimeEntry(
                date = timeentry.date,
                user_id = timeentry.user_id,
                time = data.get('time'),
                description = data.get('description'),
                ticket_id = data.get('ticket_id'),
                project_id =  data.get('project_id'),
                timer_ts = datetime.datetime.now() if data.get('timer') else None,
            )
            self.session.add(time)
        else:
            if timeentry.time != data.get('time') or \
               timeentry.project_id != data.get('project_id'):
                timeentry.modified_ts = datetime.datetime.now()

            timeentry.time = data.get('time')
            timeentry.description = data.get('description')
            timeentry.ticket_id = data.get('ticket_id')
            timeentry.project_id = data.get('project_id')

        return HTTPOk("OK")

    def delete(self):
        timeentry = self.v['timeentry']

        if timeentry.date >= datetime.date.today():
            self.session.delete(timeentry)
        else:
            timeentry.deleted = True
            timeentry.modified_ts = datetime.datetime.now()

        return HTTPNoContent("Deleted")
