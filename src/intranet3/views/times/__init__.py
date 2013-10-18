from __future__ import with_statement
import __builtin__
import datetime
from pyramid.httpexceptions import HTTPFound, HTTPNotFound, HTTPBadRequest, HTTPForbidden

from pyramid.view import view_config
from pyramid.renderers import render

from intranet3.utils.views import BaseView
from intranet3.models import User, TimeEntry, Tracker, TrackerCredentials, Project
from intranet3.helpers import previous_day, next_day, format_time
from intranet3.utils.harvest import Harvest
from intranet3.utils import excuses
from intranet3.forms.times import TimeEntryForm, AddTimeEntryForm
from intranet3.forms.common import DeleteForm
from intranet3.log import INFO_LOG
from intranet3.lib.bugs import Bugs
from intranet3.lib.times import ProtectTimeEntriesMixin, user_can_modify_timeentry

LOG = INFO_LOG(__name__)

@view_config(route_name='times_today', permission='bugs_owner')
class Today(BaseView):
    def get(self):
        today = datetime.datetime.now().date()
        url = self.request.url_for('/times/list', date=today.strftime('%d.%m.%Y'))
        return HTTPFound(url)


class GetTimeEntriesMixin(object):
    def _get_time_entries(self, date, user_id=None):
        query = self.session.query(Tracker, TimeEntry)
        if user_id:
            query = query.filter(TimeEntry.user_id==user_id)
        else:
            query = query.filter(TimeEntry.user_id==self.request.user.id)

        query = query.filter(Tracker.id==Project.tracker_id)\
                     .filter(Project.id==TimeEntry.project_id)\
                     .filter(TimeEntry.date==date)\
                     .order_by(TimeEntry.added_ts)

        return query

@view_config(route_name='times_list', permission='bugs_owner')
class List(GetTimeEntriesMixin, BaseView):
    def get(self):
        date_str = self.request.GET.get('date')
        date = datetime.datetime.strptime(date_str, '%d.%m.%Y')

        entries = self._get_time_entries(date)

        total_sum = sum(entry.time for (tracker, entry) in entries if not entry.deleted)
        form = TimeEntryForm()

        needs_justification = False
        for tracker, timeentry in entries:
            if timeentry.modified_ts.date() > timeentry.date:
                needs_justification = True

        return dict(
            date=date, entries=entries, form=form,
            user=self.request.user,
            prev_date=previous_day(date), next_date=next_day(date),
            total_sum=total_sum,
            needs_justification=needs_justification,
            justification_status=excuses.wrongtime_status(date, self.request.user.id),
            can_modify=user_can_modify_timeentry(self.request.user, date),
        )

@view_config(route_name='times_list_user')
class ListUser(GetTimeEntriesMixin, BaseView):
    def get(self):
        date_str = self.request.GET.get('date')
        date = datetime.datetime.strptime(date_str, '%d.%m.%Y')
        user_id = self.request.GET.get('user_id')
        if self.request.user.id == int(user_id):
            return HTTPFound(self.request.url_for('/times/list', date=date_str))

        if not self.request.has_perm('view') and user_id != self.request.user.id:
            return HTTPForbidden()

        user = User.query.get(user_id)
        if user is None:
            return HTTPNotFound()

        entries = self._get_time_entries(date, user_id)
        form = TimeEntryForm()

        total_sum = sum(entry.time for (tracker, entry) in entries if not entry.deleted)

        return dict(
            date=date, form=form,
            entries=entries,
            user=user,
            prev_date=previous_day(date), next_date=next_day(date),
            total_sum=total_sum,
            can_modify=self.request.has_perm('admin'),
        )

@view_config(route_name='times_list_bug')
class ListBug(GetTimeEntriesMixin, BaseView):
    def get(self):
        project_id = self.request.GET.get('project_id')
        bug_id = self.request.GET.get('bug_id')
        project = Project.query.get(project_id)

        tracker = project.tracker
        entries = self.session.query(User, TimeEntry)\
                .filter(TimeEntry.user_id==User.id)\
                .filter(TimeEntry.ticket_id==bug_id)\
                .filter(TimeEntry.project_id==project.id)
        total_sum = sum(entry.time for (user, entry) in entries if not entry.deleted)
        return dict(
            project=project, bug_id=bug_id,
            tracker=tracker,
            entries=entries,
            total_sum=total_sum
        )


@view_config(route_name='times_add_entry_to_one_of_yourbugs')
class AddEntryToOneOfYourBugs(BaseView):
    def get(self):
        date = datetime.datetime.strptime(self.request.GET.get('date'), '%d.%m.%Y')
        bugs = Bugs(self.request).get_user()
        form = TimeEntryForm()
        return dict(
            date=date, form=form,
            bugs=(bug for bug in bugs if bug.project),
            user=self.request.user,
        )


@view_config(route_name='times_add', permission='bugs_owner')
class Add(ProtectTimeEntriesMixin, GetTimeEntriesMixin, BaseView):
    def _add_to_harvest(self, form):
        PROJECT_ID = 2904241 # TODO
        TASK_ID = 187504 # Programming
        time = form.time.data
        if not time:
            return
        desc = form.description.data
        tickets_id = form.ticket_id.data
        if tickets_id:
            tickets_id = '#'+' ,#'.join([str(ticket_id) for ticket_id in tickets_id])
            notes = 'Tickets: %s - %s' % (tickets_id, desc)
        else:
            notes = desc

        query = self.session.query
        tracker = Tracker.query.filter(Tracker.type=='harvest').first()
        if not tracker:
            return
        credentials = query(TrackerCredentials)\
                            .filter(TrackerCredentials.tracker_id==tracker.id)\
                            .filter(TrackerCredentials.user_id==self.request.user.id).first()
        if not credentials:
            self.flash(self._(u'Please add Harvest credentials'))
            return
        login, password = credentials.login, credentials.password
        harvest = Harvest(tracker.url, login, password)
        data = dict(
            notes=notes,
            hours=time,
            project_id=PROJECT_ID,
            task_id=TASK_ID,
        )
        response = harvest.add(data)
        if response:
            self.flash(self._(u'Time entry added to Harvest'))
        else:
            self.flash(self._(u'Wrong login or password'))

    def post(self):
        date = self.v['date']
        form = AddTimeEntryForm(self.request.POST)

        if self.request.POST.get('start_timer'):
            form.timer.data = u'1'
            if not form.time.data:
                form.time.data = 0.0
        else:
            form.timer.data = u''

        user = self.v.get('user', self.request.user)

        next_ = self.request.GET.get('next')
        if not next_:
            next_ = self.request.url_for(
                '/times/list',
                date=date.strftime('%d.%m.%Y')
            )

        if form.validate():
            notifications_data = []
            now = datetime.datetime.now()
            project_id = form.project_id.data
            project = Project.query.get(project_id) if project_id else None
            if isinstance(form.ticket_id.data, __builtin__.list):
                count = len(form.ticket_id.data)
                for ticket_id in form.ticket_id.data:
                    time = TimeEntry(
                        date = date,
                        user_id=user.id,
                        time = form.time.data / count,
                        description = form.description.data,
                        ticket_id = ticket_id,
                        project_id = project_id if project_id else None,
                        timer_ts = datetime.datetime.now() if form.timer.data and count == 1 else None,
                        frozen = bool(self.request.POST.get('start_timer')) and count == 1
                    )
                    self.session.add(time)
                    notifications_data.append((now, date, self.request.user, project, form.time.data / count, ticket_id, form.description.data))
            else:
                time = TimeEntry(
                    date = date,
                    user_id=user.id,
                    time = form.time.data,
                    description = form.description.data,
                    ticket_id = form.ticket_id.data,
                    project_id = project_id if project_id else None,
                    timer_ts = datetime.datetime.now() if form.timer.data else None,
                    frozen = bool(self.request.POST.get('start_timer'))
                )
                self.session.add(time)
                notifications_data.append((now, date, self.request.user, project, form.time.data, form.ticket_id.data, form.description.data))

            if form.add_to_harvest.data:
                self._add_to_harvest(form)
            self.flash(self._(u'Time entry added'))
            LOG(u'Time entry added')

            return HTTPFound(location=next_)
        return dict(
            user=user,
            date=date,
            form=form,
            next=next_ or self.request.url_for(
                '/times/list',
                date=date.strftime('%d.%m.%Y')
            )
        )


@view_config(route_name='times_edit', permission='bugs_owner')
class Edit(ProtectTimeEntriesMixin, BaseView):
    def get(self):
        timeentry = self.v['timeentry']

        next_ = self.request.GET.get('next')
        if not next_:
            next_ = self.request.url_for(
                '/times/list',
                date=timeentry.date.strftime('%d.%m.%Y'),
            )
        form = TimeEntryForm(obj=timeentry)
        date = timeentry.date

        return dict(
            timeentry_id=timeentry.id,
            form=form,
            date=date,
            next=next_,
        )

    def post(self):
        timeentry = self.v['timeentry']

        next_ = self.request.GET.get('next')
        if not next_:
            next_ = self.request.url_for(
                '/times/list',
                date=timeentry.date.strftime('%d.%m.%Y'),
            )

        form = TimeEntryForm(self.request.POST, obj=timeentry)
        date = timeentry.date
        today = datetime.date.today()

        if form.validate():
            if timeentry.project_id != int(form.project_id.data) and today > date:
                timeentry.deleted = True
                timeentry.modified_ts = datetime.datetime.now()
                time = TimeEntry(
                    date=date,
                    user_id = timeentry.user_id,
                    time = form.time.data,
                    description = form.description.data,
                    ticket_id = form.ticket_id.data,
                    project_id = form.project_id.data if form.project_id.data else None,
                    timer_ts = datetime.datetime.now() if form.timer.data else None
                )
                self.session.add(time)
            else:
                ticket_id = form.ticket_id.data

                if timeentry.time != form.time.data or\
                   timeentry.project_id != form.project_id.data:
                    timeentry.modified_ts = datetime.datetime.now()

                timeentry.time = form.time.data
                timeentry.description = form.description.data
                timeentry.ticket_id = ticket_id
                timeentry.project_id = form.project_id.data if form.project_id.data else None

            self.flash(self._(u'Time entry saved'))
            LOG(u'Time entry saved')
            return HTTPFound(next_)

        return dict(
            timeentry_id=timeentry.id,
            form=form,
            date=date,
            next=next_,
        )


@view_config(route_name='times_delete', renderer='intranet3:templates/common/delete.html', permission='bugs_owner')
class Delete(ProtectTimeEntriesMixin, BaseView):
    def post(self):
        form = DeleteForm(self.request.POST)
        timeentry = self.v['timeentry']

        next_ = self.request.GET.get('next')
        if not next_:
            next_ = self.request.url_for(
                '/times/list',
                date=timeentry.date.strftime('%d.%m.%Y'),
            )

        if form.validate():
            # if time entry was added today or later,
            # it might be just removed from the database
            if timeentry.date >= datetime.date.today():
                self.session.delete(timeentry)
            else:
                # otherwise timeentry must stay in the DB
                # to show as 'late' modification
                timeentry.deleted = True
                timeentry.modified_ts = datetime.datetime.now()
            LOG(u"Deleted time entry")
            self.flash(self._(u"Deleted time entry"))
            return HTTPFound(next_)

        return dict(
            type_name=self._(u'time entry'),
            title=self._(u'from ${date} for ${desc}', date=timeentry.date.strftime('%d.%m.%Y'), desc=timeentry.description),
            url=self.request.url_for(
                '/times/delete',
                timeentry_id=timeentry.id,
                next=next_,
            ),
            back_url=next_,
            form=form
        )

    def get(self):
        """
        Mark timeentry as deleted.

        We are not removing entries from the database, because we need to know, when
        any changes to time entries happened.
        """
        timeentry = self.v['timeentry']

        next_ = self.request.GET.get('next')
        if not next_:
            next_ = self.request.url_for(
                '/times/list',
                date=timeentry.date.strftime('%d.%m.%Y'),
            )
        form = DeleteForm()
        return dict(
            type_name=self._(u'time entry'),
            title=self._(u'from ${date} for ${desc}', date=timeentry.date.strftime('%d.%m.%Y'), desc=timeentry.description),
            url=self.request.url_for(
                '/times/delete',
                timeentry_id=timeentry.id,
                next=next_,
            ),
            back_url=next_,
            form=form
        )

@view_config(route_name='times_ajax_add', renderer='json')
class AjaxAdd(ProtectTimeEntriesMixin, GetTimeEntriesMixin, BaseView):
    def post(self):
        if not self.request.is_xhr:
            return HTTPBadRequest()

        date = self.v['date']
        form = TimeEntryForm(self.request.POST)

        if form.validate():
            project_id = form.project_id.data
            time = TimeEntry(
                date = date,
                user_id = self.request.user.id,
                time = form.time.data,
                description = form.description.data,
                ticket_id = form.ticket_id.data,
                project_id = project_id if project_id else None
            )
            self.session.add(time)
            LOG(u'Ajax - Time entry added')

            entries = self._get_time_entries(date)
            total_sum = sum(entry.time for (tracker, entry) in entries if not entry.deleted)
            template = render(
                '/times/_list.html',
                dict(entries=entries, total_sum=total_sum),
                request=self.request
            )

            return dict(status='success', html=template)

        errors = u'<br />'.join((u"%s - %s" % (field, u', '.join(errors)) for field, errors in form.errors.iteritems()))
        return dict(status='error', errors=errors)


@view_config(route_name='times_start_timer', renderer='json')
class StartTimer(GetTimeEntriesMixin, BaseView):
    def post(self):
        timeentry_id = self.request.GET.get('timeentry_id')
        timeentry = TimeEntry.query.get(timeentry_id)
        if timeentry.user_id == self.request.user.id and not timeentry.timer_ts:
            timeentry.timer_ts = datetime.datetime.now()
            timeentry.modified_ts = datetime.datetime.now()
            timeentry.frozen = True
            return dict(status='success')
        else:
            return HTTPForbidden()

@view_config(route_name='times_stop_timer', renderer='json')
class StopTimer(GetTimeEntriesMixin, BaseView):
    def post(self):
        timeentry_id = self.request.GET.get('timeentry_id')
        timeentry = TimeEntry.query.get(timeentry_id)
        if timeentry.user_id == self.request.user.id\
        and timeentry.timer_ts:
            seconds = (datetime.datetime.now() - timeentry.timer_ts).seconds
            timeentry.time += float(seconds) / 3600
            timeentry.timer_ts = None
            timeentry.modified_ts = datetime.datetime.now()

            entries = self._get_time_entries(timeentry.date)
            total_sum = sum(entry.time for (tracker, entry) in entries if not entry.deleted)
            return dict(
                status='success',
                time=format_time(timeentry.time),
                total_sum=format_time(total_sum)
            )
        else:
            return HTTPForbidden()

@view_config(route_name='times_freeze_time_entry', renderer='json')
class FreezeTimeEntry(BaseView):
    """
        Mark time entry as frozen
    """
    def post(self):
        timeentry_id = self.request.GET.get('timeentry_id')
        timeentry = TimeEntry.query.get(timeentry_id)
        if timeentry.user_id != self.request.user.id:
            return HTTPForbidden()

        back_url = self.request.url_for('/times/list', date=timeentry.date.strftime('%d.%m.%Y'))
        timeentry.frozen = True
        timeentry.modified_ts = datetime.datetime.now()
        return HTTPFound(back_url)

@view_config(route_name='times_thaw_time_entry', renderer='json')
class ThawTimeEntry(BaseView):
    """
        Mark time entry as unfrozen
    """
    def post(self):
        timeentry_id = self.request.GET.get('timeentry_id')
        timeentry = TimeEntry.query.get(timeentry_id)
        if timeentry.user_id != self.request.user.id:
            return HTTPForbidden()

        back_url = self.request.url_for('/times/list', date=timeentry.date.strftime('%d.%m.%Y'))
        timeentry.frozen = False
        timeentry.modified_ts = datetime.datetime.now()
        return HTTPFound(back_url)
