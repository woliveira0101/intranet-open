# coding: utf-8
import calendar
import datetime

import colander

from pyramid.httpexceptions import HTTPBadRequest, HTTPCreated, HTTPForbidden, HTTPNotFound, HTTPOk, HTTPNoContent
from pyramid.view import view_config

from intranet3.forms.times import time_filter
from intranet3.helpers import previous_day, next_day, format_time
from intranet3.lib.bugs import Bugs
from intranet3.models import User, Project, TimeEntry, Tracker, Project
from intranet3.utils.views import ApiView
from intranet3.views.times import GetTimeEntriesMixin
from intranet3.log import INFO_LOG

from intranet3.schemas.times import AddEntrySchema, EditEntrySchema, AddOneOfOwnBugsSchema

LOG = INFO_LOG(__name__)


def user_can_modify(user, date):
    if user.has_perm('admin'):
        return True

    # User Can modify entry only in current month
    today = datetime.date.today()
    if date.month == today.month:
        return True

    return False


@view_config(route_name='api_time_collection', renderer='json', permission='client_or_freelancer')
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

        if self.request.method == "POST":
            if 'date' in self.request.GET:
                if not user_can_modify(self.request, date):
                    raise HTTPForbidden()

            if 'user_id' in self.request.GET:
                if not self.request.has_perm('admin'):
                    raise HTTPForbidden()

        self.v['user'] = user
        self.v['date'] = date

    def _get_params(self):
        date_str = self.request.GET.get('date', None)
        try:
            user_id = int(self.request.GET.get('user_id', self.request.user.id))
        except ValueError:
            raise HTTPBadRequest("Wrong User ID")
        if date_str is not None:
            date = datetime.datetime.strptime(date_str, '%d.%m.%Y')
        else:
            date = datetime.datetime.now().date()

        user = User.query.get(user_id)

        if user is None:
            raise HTTPNotFound("User Not Found")

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
            project_id = data.get('project_id', None)
            project = Project.query.get(project_id) if project_id else None

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
        except colander.Invalid as e:
            raise HTTPBadRequest(e.asdict())

        return HTTPCreated('OK')


@view_config(route_name='api_time', renderer='json', permission='client_or_freelancer')
class Time(ApiView):

    def protect(self):
        '''
            User can edit `TimeEntry` only during current month
        '''
        if self.request.method in ["PUT", "DELETE"]:
            if 'id' in self.request.matchdict:
                timeentry_id = self.request.matchdict.get('id')
                timeentry = TimeEntry.query.get(timeentry_id)

                if not user_can_modify(self.request, timeentry.date):
                    raise HTTPForbidden()

                if not self.request.has_perm('admin'):
                    if timeentry.deleted:
                        raise HTTPBadRequest()
                    elif self.request.user.id != timeentry.user_id:
                        raise HTTPBadRequest()

                self.v['timeentry'] = timeentry

    def get(self):
        timeentry_id = self.request.matchdict['id']

        timeentry = TimeEntry.query.get(timeentry_id)
        if timeentry is None:
            raise HTTPNotFound("Not Found")

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

            if timeentry.project_id != data.get('project_id') and today > timeentry.date:
                timeentry.deleted = True
                timeentry.modified_ts = datetime.datetime.now() 

                time = TimeEntry(
                    date = timeentry.date,
                    user_id = timeentry.user_id,
                    time = data.get('time'),
                    description = data.get('description'),
                    ticket_id = data.get('ticket_id'),
                    project_id =  data.get('project_id', None),
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
                timeentry.project_id = data.get('project_id', None)

        except colander.Invalid as e:
            raise HTTPBadRequest(e.asdict())

        return HTTPOk("OK")

    def delete(self):
        timeentry = self.v['timeentry']

        if timeentry.date >= datetime.date.today():
            self.session.delete(timeentry)
        else:
            timeentry.deleted = True
            timeentry.modified_ts = datetime.datetime.now()

        return HTTPNoContent("Deleted")
