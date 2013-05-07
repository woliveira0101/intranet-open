import json
import datetime

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPForbidden, HTTPBadRequest

from intranet3.utils.views import BaseView
from intranet3.forms.scrum import SprintForm
from intranet3.forms.common import DeleteForm
from intranet3.models import Sprint, ApplicationConfig, Tracker, User, Project
from intranet3 import helpers as h

from intranet3.log import INFO_LOG, ERROR_LOG
from intranet3.lib.scrum import SprintWrapper, get_velocity_chart_data, move_blocked_to_the_end
from intranet3.lib.times import TimesReportMixin, Row
from intranet3.lib.bugs import Bugs
from intranet3.forms.times import ProjectTimeForm
from intranet3.forms.scrum import SprintListFilterForm

LOG = INFO_LOG(__name__)
ERROR = ERROR_LOG(__name__)


@view_config(route_name='scrum_sprint_list', permission='client')
class List(BaseView):
    def get(self):
        client = self.request.user.get_client()

        form = SprintListFilterForm(self.request.GET, client=client)
        active_only = form.active_only.data
        limit = form.limit.data or 10
        project = None

        sprints = Sprint.query.order_by(Sprint.start.desc())
        all_sprints = None

        if form.project_id.data and form.project_id.data != 'None':
            project_id = int(form.project_id.data)
            project = Project.query.get(project_id)
            sprints = sprints.filter(Sprint.project_id == project_id)
            all_sprints = Sprint.query.order_by(Sprint.start)\
                                .filter(Sprint.project_id == project_id)

        if client:
            sprints = sprints.filter(Sprint.client_id == client.id)
            if all_sprints:
                all_sprints = all_sprints.filter(Sprint.client_id == client.id)

        if active_only:
            sprints = sprints.filter(Sprint.end >= datetime.date.today())

        if limit:
            sprints.limit(limit)

        sprints = sprints.all()

        if all_sprints:
            velocity_chart_data = get_velocity_chart_data(all_sprints)

        if sprints:
            stats = dict(
                worked_hours=sum([s.worked_hours for s in sprints]) / len(sprints),
                achieved=sum([s.achieved_points for s in sprints]) / len(sprints),
                commited=sum([s.commited_points for s in sprints]) / len(sprints),
                velocity=sum([s.velocity for s in sprints]) / len(sprints),
            )
        else:
            stats = None
        return dict(
            sprints=sprints,
            form=form,
            velocity_chart_data=velocity_chart_data if all_sprints else None,
            stats=stats,
            project=project
        )


class FetchBugsMixin(object):
    def _fetch_bugs(self, sprint):
        config_obj = ApplicationConfig.get_current_config()
        user = User.query.get(config_obj.hours_ticket_user_id)
        bugs = Bugs(self.request, user).get_sprint(sprint)
        return bugs


class ClientProtectionMixin(object):
    def protect(self):
        if not self.request.is_user_in_group('client'):
            return
        sprint_id = self.request.GET.get('sprint_id')
        sprint = Sprint.query.get(sprint_id)
        client = self.request.user.get_client()
        if client.id != sprint.client_id:
            raise HTTPForbidden()


@view_config(route_name='scrum_sprint_show', permission='client')
class Show(ClientProtectionMixin, FetchBugsMixin, BaseView):
    def get(self):
        sprint_id = self.request.GET.get('sprint_id')
        sprint = Sprint.query.get(sprint_id)
        project = Project.query.get(sprint.project_id)
        bugs = self._fetch_bugs(sprint)
        bugs = sorted(bugs, cmp=h.sorting_by_priority)
        bugs = move_blocked_to_the_end(bugs)

        tracker = Tracker.query.get(sprint.project.tracker_id)
        sw = SprintWrapper(sprint, bugs, self.request)
        return dict(
            sprint=sprint,
            project=project,
            bugs=bugs,
            tracker=tracker,
            info=sw.get_info(),
        )


@view_config(route_name='scrum_sprint_board', permission='client')
class Board(ClientProtectionMixin, FetchBugsMixin, BaseView):
    def get(self):
        sprint_id = self.request.GET.get('sprint_id')
        sprint = Sprint.query.get(sprint_id)
        project = Project.query.get(sprint.project_id)
        bugs = self._fetch_bugs(sprint)

        sw = SprintWrapper(sprint, bugs, self.request)
        board = sw.get_board()

        return dict(
            board=board,
            sprint=sprint,
            project=project,
            info=sw.get_info(),
            bug_list_url=lambda bugs: sprint.project.get_bug_list_url([bug.id for bug in bugs]),
        )


@view_config(route_name='scrum_sprint_times', permission='client')
class Times(ClientProtectionMixin, TimesReportMixin, FetchBugsMixin, BaseView):
    def dispatch(self):
        sprint_id = self.request.GET.get('sprint_id')
        sprint = Sprint.query.get(sprint_id)
        bugs = self._fetch_bugs(sprint)
        sw = SprintWrapper(sprint, bugs, self.request)

        client = self.request.user.get_client()
        form = ProjectTimeForm(self.request.GET, client=client)

        if not self.request.GET.get('submited'):
            # ugly hack
            form.group_by_bugs.data = True
            form.group_by_user.data = True

        if not form.validate():
            return dict(form=form, sprint=sprint)

        group_by = True, True, form.group_by_bugs.data, form.group_by_user.data

        uber_query = self._prepare_uber_query_for_sprint(sprint, bugs)
        entries = uber_query.all()

        if self.request.GET.get('excel'):
            from intranet3.lib.times import dump_entries_to_excel
            file, response = dump_entries_to_excel(entries)
            return response

        entries_sum = sum([e[-1] for e in entries])

        participation_of_workers = self._get_participation_of_workers(entries)

        tickets_id = ','.join([str(e[2]) for e in entries])
        trackers_id = ','.join([str(e[4].id) for e in entries])

        rows = Row.from_ordered_data(entries, group_by)

        return dict(
            rows=rows,
            entries_sum=entries_sum,
            form=form,
            info=sw.get_info(),
            sprint=sprint,
            participation_of_workers=participation_of_workers,
            participation_of_workers_sum=sum([time[1] for time in participation_of_workers]),
            trackers_id=trackers_id, tickets_id=tickets_id,
        )

@view_config(route_name='scrum_sprint_charts', permission='client')
class Charts(ClientProtectionMixin, FetchBugsMixin, BaseView):
    def get(self):
        sprint_id = self.request.GET.get('sprint_id')
        sprint = Sprint.query.get(sprint_id)
        project = Project.query.get(sprint.project_id)
        bugs = self._fetch_bugs(sprint)
        sw = SprintWrapper(sprint, bugs, self.request)
        burndown = sw.get_burndown_data()
        tracker = Tracker.query.get(sprint.project.tracker_id)

        entries, sum_ = sw.get_worked_hours()
        entries.insert(0, ('Employee', 'Time'))
        piechart_data = json.dumps(entries)

        return dict(
            tracker=tracker,
            sprint=sprint,
            project = project,
            bugs=bugs,
            charts_data=json.dumps(burndown),
            piechart_data=piechart_data,
            info=sw.get_info(),
        )


@view_config(route_name='scrum_sprint_edit', permission='coordinator')
class Edit(BaseView):
    def dispatch(self):
        sprint_id = self.request.GET.get('sprint_id')
        sprint = Sprint.query.get(sprint_id)
        form = SprintForm(self.request.POST, obj=sprint)
        if self.request.method == 'POST' and form.validate():
            project_id = int(form.project_id.data)
            project = Project.query.get(project_id)
            sprint.name = form.name.data
            sprint.client_id = project.client_id
            sprint.project_id = project.id
            sprint.start = form.start.data
            sprint.end = form.end.data
            sprint.goal = form.goal.data
            self.session.add(sprint)
            self.flash(self._(u"Sprint edited"))
            LOG(u"Sprint edited")
            url = self.request.url_for('/scrum/sprint/show', sprint_id=sprint.id)
            return HTTPFound(location=url)
        return dict(
            form=form,
            sprint=sprint
        )


@view_config(route_name='scrum_sprint_add', permission='coordinator')
class Add(BaseView):
    def dispatch(self):
        form = SprintForm(self.request.POST)
        if self.request.method == 'POST' and form.validate():
            project_id = int(form.project_id.data)
            project = Project.query.get(project_id)
            sprint = Sprint(
                name=form.name.data,
                client_id=project.client_id,
                project_id=project.id,
                start=form.start.data,
                end=form.end.data,
                goal=form.goal.data,
            )
            self.session.add(sprint)
            self.session.flush()
            self.flash(self._(u"New sprint added"))
            LOG(u"Sprint added")
            url = self.request.url_for('/scrum/sprint/show', sprint_id=sprint.id)
            return HTTPFound(location=url)
        return dict(
            form=form
        )


@view_config(route_name='scrum_sprint_delete',
    renderer='intranet3:templates/common/delete.html',
    permission='coordinator')
class Delete(BaseView):

    def dispatch(self):
        sprint_id = self.request.GET.get('sprint_id')
        sprint =  Sprint.query.get(sprint_id)
        form = DeleteForm(self.request.POST)
        if self.request.method == 'POST' and form.validate():
            self.session.delete(sprint)
            back_url = self.request.url_for('/scrum/sprint/list')
            return HTTPFound(location=back_url)
        return dict(
            type_name=u'sprint',
            title=u'%s' % sprint.name,
            url=self.request.url_for('/scrum/sprint/delete', sprint_id=sprint.id),
            back_url=self.request.url_for('/scrum/sprint/list'),
            form=form
        )
