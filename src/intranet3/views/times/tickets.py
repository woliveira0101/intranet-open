from __future__ import with_statement

from pyramid.view import view_config
from pyramid.renderers import render

from intranet3.utils.views import BaseView
from intranet3.models import User, TimeEntry, Tracker, Project, Client
from intranet3.forms.times import ProjectsTimeForm, TimeEntryForm
from intranet3.log import INFO_LOG, WARN_LOG, ERROR_LOG, DEBUG_LOG, EXCEPTION_LOG
from intranet3.lib.times import TimesReportMixin, HTMLRow, dump_entries_to_excel

LOG = INFO_LOG(__name__)
WARN = WARN_LOG(__name__)
ERROR = ERROR_LOG(__name__)
DEBUG = DEBUG_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)


MAX_TIMEOUT = 20 # DON'T WAIT LONGER THAN DEFINED TIMEOUT
MAX_TICKETS_PER_REQUEST = 50 # max number of ticket ids to include in a single request to tracker

@view_config(route_name='times_tickets_excel', permission='client')
class Excel(BaseView):
    def get(self):
        client = self.request.user.get_client()
        form = ProjectsTimeForm(formdata=self.request.GET, client=client)
        if not form.validate():
            return render('time/tickets_report/projects_report.html', dict(form=form))

        query = self.session.query
        start_date, end_date = form.date_range.data
        projects = form.projects.data
        users = form.users.data
        ticket_choice = form.ticket_choice.data
        group_by = (
            form.group_by_client.data,
            form.group_by_project.data,
            form.group_by_bugs.data,
            form.group_by_user.data
        )
        bigger_than = form.bigger_than.data

        LOG(u'Tickets report %r - %r - %r' % (start_date, end_date, projects))

        uber_query = query(Client, Project, TimeEntry.ticket_id, User, Tracker, TimeEntry.description, TimeEntry.date, TimeEntry.time)
        uber_query = uber_query.filter(TimeEntry.user_id==User.id)\
                               .filter(TimeEntry.project_id==Project.id)\
                               .filter(Project.tracker_id==Tracker.id)\
                               .filter(Project.client_id==Client.id)

        uber_query = uber_query.filter(TimeEntry.project_id.in_(projects))\
                               .filter(TimeEntry.date>=start_date)\
                               .filter(TimeEntry.date<=end_date)\
                               .filter(TimeEntry.deleted==False)

        if ticket_choice == 'without_bug_only':
            uber_query = uber_query.filter(TimeEntry.ticket_id=='')
        elif ticket_choice == 'meetings_only':
            meeting_ids = [t['value'] for t in TimeEntryForm.PREDEFINED_TICKET_IDS]
            uber_query = uber_query.filter(TimeEntry.ticket_id.in_(meeting_ids))

        if users:
            uber_query = uber_query.filter(User.id.in_(users))

        uber_query = uber_query.order_by(Client.name, Project.name, TimeEntry.ticket_id, User.name)
        entries = uber_query.all()
        file, response = dump_entries_to_excel(entries, group_by, bigger_than)

        return response


@view_config(route_name='times_tickets_report', permission='client')
class Report(TimesReportMixin, BaseView):
    def dispatch(self):
        client = self.request.user.get_client()
        form = ProjectsTimeForm(self.request.GET, client=client)

        if not self.request.GET or not form.validate():
            return dict(form=form)

        start_date, end_date = form.date_range.data
        projects = form.projects.data

        if not projects:
            projects = [p[0] for p in form.projects.choices]

        users = form.users.data
        bigger_than = form.bigger_than.data
        ticket_choice = form.ticket_choice.data
        group_by = (
            form.group_by_client.data,
            form.group_by_project.data,
            form.group_by_bugs.data,
            form.group_by_user.data
        )

        LOG(u'Tickets report %r - %r - %r' % (start_date, end_date, projects))

        uber_query = self._prepare_uber_query(
            start_date, end_date, projects, users, ticket_choice,
        )

        entries = uber_query.all()

        participation_of_workers = self._get_participation_of_workers(entries)

        tickets_id = ','.join([str(e[2]) for e in entries])
        trackers_id = ','.join([str(e[4].id) for e in entries])

        rows, entries_sum = HTMLRow.from_ordered_data(entries, group_by, bigger_than)

        return dict(
            rows=rows,
            entries_sum=entries_sum,
            form=form,
            participation_of_workers=participation_of_workers,
            participation_of_workers_sum=sum([time[1] for time in participation_of_workers]),
            trackers_id=trackers_id, tickets_id=tickets_id,
        )

