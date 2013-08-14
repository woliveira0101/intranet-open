# coding: utf-8
import calendar
import datetime

from pyramid.httpexceptions import HTTPBadRequest, HTTPCreated, HTTPForbidden, HTTPNotFound, HTTPOk, HTTPNoContent
from pyramid.view import view_config

from intranet3.forms.times import time_filter
from intranet3.helpers import previous_day, next_day, format_time
from intranet3.models import User, Project, TimeEntry
from intranet3.utils.views import ApiView
from intranet3.views.times import GetTimeEntriesMixin
from intranet3.log import INFO_LOG

from intranet3.schemas.times import AddEntrySchema, EditEntrySchema

LOG = INFO_LOG(__name__)


def _date_to_string(date):
    return date.strftime("%d.%m.%Y")


def user_can_modify(user, timeentry_date):
    if user.has_perm('admin'):
        return True

    today = datetime.datetime().now()
    first_day, days_in_month = calendar.monthrange(today.year, today.month)
    last_day = datetime.date(today.year, today.month, days_in_month)

    return (first_day < timeentry_ < last_day)


@view_config(route_name='api_times', renderer='json', permission='client_or_freelancer')
class Times(GetTimeEntriesMixin, ApiView):

    def _entries_serializer(self, objs):
        l = []
        for tracker, entry in objs:
            response = {
                'id': entry.id,
                'desc': entry.description,
                'added': _date_to_string(entry.added_ts),
                'modified': _date_to_string(entry.modified_ts),
                'ticket_id': entry.ticket_id,
                'tracker_url': tracker.get_bug_url(entry.ticket_id),
                'project': None
            }

            if entry.project:
                response.update({
                    'project': {
                        'client_name': entry.project.client.name,
                        'project_name': entry.project.name,
                    }
                })


            l.append(response)
        return l

    def protect(self):
        '''
            User can edit `TimeEntry` only during current month
        '''
        method = self.request.method.lower()
        if method in ["put", "delete"]:  # Protect update!
            if 'timeentry_id' in self.request.GET:
                timeentry_id = self.request.GET.get('timeentry_id')
                timeentry = TimeEntry.query.get(timeentry_id)
                date = timeentry.date

                if not user_can_modify(self.request, date):
                    raise HTTPForbidden()

                if not self.request.has_perm('admin'):
                    if timeentry.deleted:
                        raise HTTPBadRequest
                    elif self.request.user.id != timeentry.user_id:
                        raise HTTPBadRequest()

                self.v['timeentry'] = timeentry

    def get_params(self):
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
        (user, date) = self.get_params()

        entries = self._get_time_entries(date, user.id)
        total_sum = sum(entry.time for (tracker, entry) in entries if not entry.deleted)

        return {
            'date': _date_to_string(date),
            'user_id': user.id,
            'previous_day': _date_to_string(previous_day(date)),
            'next_day': _date_to_string(next_day(date)),
            'total_sum': total_sum,
            'entries': self._entries_serializer(entries)
        }

    def post(self):
        (user, date) = self.params()

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
        except Invalid as e:
            raise HTTPBadRequest(e.asdict())

        return HTTPCreated('OK')

    def put(self):
        timeentry = self.v['timeentry']
        today = datetime.date.today()

        try:
            schema = EditEntrySchema()
            data = schema.deserialize(self.request.POST)
            import ipdb; ipdb.set_trace()
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

        except Invalid as e:
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


class EntryToOneOfOwnBugs(ApiView):

    def get(self):
        return {
            'todo': "project, ticket id"
        }

    def post(self):
        return {
            'todo': 'request.POST[time,description,] /:ticket_id'
        }