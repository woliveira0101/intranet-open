import json
import datetime

import markdown
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPForbidden, HTTPNotFound
from pyramid.response import Response

from intranet3.utils.views import BaseView
from intranet3.forms.scrum import SprintForm
from intranet3.forms.common import DeleteForm
from intranet3.models import (
    Sprint,
    ApplicationConfig,
    Tracker,
    User,
    Project,
    DBSession,
)
from intranet3 import helpers as h

from intranet3.log import INFO_LOG, ERROR_LOG
from intranet3.lib.scrum import SprintWrapper, get_velocity_chart_data
from intranet3.lib.times import TimesReportMixin, HTMLRow
from intranet3.lib.bugs import Bugs
from intranet3.forms.times import ProjectTimeForm
from intranet3.forms.scrum import SprintListFilterForm

LOG = INFO_LOG(__name__)
ERROR = ERROR_LOG(__name__)


@view_config(route_name='scrum_sprint_list', permission='can_view_sprints')
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
        self.v['sprint'] = sprint
        self.v['client'] = client
        if client.id != sprint.client_id:
            raise HTTPForbidden()

@view_config(route_name='scrum_sprint_field', permission='can_view_sprints')
class Field(ClientProtectionMixin, BaseView):
    def get(self):
        field = self.request.GET.get('field')
        sprint_id = self.request.GET.get('sprint_id')
        sprint = Sprint.query.get(sprint_id)

        if field == 'retrospective_note':
            result = sprint.retrospective_note
            header = 'Retrospective note'
        else:
            raise HTTPNotFound

        md = markdown.Markdown()
        result = md.convert(result)
        result = '<h2 class="content-header">%s</h2>%s' % (header, result)
        return Response(result)


class BaseSprintView(BaseView):
    def tmpl_ctx(self):

        sprint = self.v.get('sprint')
        if not sprint:
            sprint_id = self.request.GET.get('sprint_id')
            sprint = Sprint.query.get(sprint_id)
        project = Project.query.get(sprint.project_id)

        sprint.calculate_velocities()

        self.v['project'] = project
        self.v['sprint'] = sprint

        prev_sprint = DBSession.query(Sprint)\
            .filter(Sprint.project_id == sprint.project_id)\
            .filter(Sprint.start < sprint.start)\
            .order_by(Sprint.start.desc()).first()

        next_sprint = DBSession.query(Sprint) \
            .filter(Sprint.project_id == sprint.project_id) \
            .filter(Sprint.start > sprint.start) \
            .order_by(Sprint.start.asc()).first()

        return dict(
            project=project,
            sprint=sprint,
            prev_sprint=prev_sprint,
            next_sprint=next_sprint,
        )


@view_config(route_name='scrum_sprint_show', permission='can_view_sprints')
class Show(ClientProtectionMixin, FetchBugsMixin, BaseSprintView):
    def get(self):
        sprint = self.v['sprint']
        bugs = self._fetch_bugs(sprint)
        bugs = sorted(bugs, cmp=h.sorting_by_priority)
        tracker = Tracker.query.get(sprint.project.tracker_id)

        sw = SprintWrapper(sprint, bugs, self.request)

        for bug in bugs:
            bug.danger = sw.board.is_completed(bug) and (
                bug.scrum.velocity <= (0.7 * sprint.story_velocity)
                or bug.scrum.velocity >= (1.3 * sprint.story_velocity)
            )

        return dict(
            tracker=tracker,
            board=sw.board,
            info=sw.get_info(),
            str_date=self._sprint_daterange(sprint.start, sprint.end),
            sprint_tabs=sw.get_tabs(),
        )

    def _sprint_daterange(self, st, end):
        return '%s - %s' % (st.strftime('%d-%m-%Y'), end.strftime('%d-%m-%Y'))


@view_config(route_name='scrum_sprint_board', permission='can_view_sprints')
class Board(ClientProtectionMixin, FetchBugsMixin, BaseSprintView):
    def get(self):
        sprint = self.v['sprint']
        bugs = self._fetch_bugs(sprint)

        allowed_colors = None
        if 'color' in self.request.GET:
            color = '#{}'.format(self.request.GET['color'])
            allowed_colors = [color]

        sw = SprintWrapper(sprint, bugs, self.request, allowed_colors)

        board_schema = sprint.get_board()

        filter_colors = [
            {"color": "", "name": "All"},
        ]
        filter_colors.extend(board_schema['colors'])

        return dict(
            board=sw.board,
            info=sw.get_info(),
            sprint_tabs=sw.get_tabs(),
            filter_colors=json.dumps(filter_colors),
            sprint_id=sprint.id,
        )


@view_config(route_name='scrum_sprint_times', permission='can_view_sprints')
class Times(ClientProtectionMixin, TimesReportMixin, FetchBugsMixin,
            BaseSprintView):
    def dispatch(self):
        sprint = self.v['sprint']
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
        bigger_than = form.bigger_than.data
        ticket_choice = form.ticket_choice.data

        uber_query = self._prepare_uber_query_for_sprint(
            sprint, bugs, ticket_choice
        )
        entries = uber_query.all()

        if self.request.GET.get('excel'):
            from intranet3.lib.times import dump_entries_to_excel
            file, response = dump_entries_to_excel(
                entries, group_by, bigger_than
            )
            return response

        participation_of_workers = self._get_participation_of_workers(entries)

        tickets_id = ','.join([str(e[2]) for e in entries])
        trackers_id = ','.join([str(e[4].id) for e in entries])

        rows, entries_sum = HTMLRow.from_ordered_data(
            entries, group_by, bigger_than
        )

        return dict(
            rows=rows,
            entries_sum=entries_sum,
            form=form,
            info=sw.get_info(),
            participation_of_workers=participation_of_workers,
            participation_of_workers_sum=sum(
                [time[1] for time in participation_of_workers]
            ),
            trackers_id=trackers_id, tickets_id=tickets_id,
            sprint_tabs=sw.get_tabs()
        )

@view_config(route_name='scrum_sprint_charts', permission='can_view_sprints')
class Charts(ClientProtectionMixin, FetchBugsMixin, BaseSprintView):
    def get(self):
        sprint = self.v['sprint']
        bugs = self._fetch_bugs(sprint)
        sw = SprintWrapper(sprint, bugs, self.request)
        burndown = sw.get_burndown_data()
        tracker = Tracker.query.get(sprint.project.tracker_id)

        entries, sum_, bugs_sum = sw.get_worked_hours()
        entries.insert(0, ('Employee', 'Time'))
        piechart_data = json.dumps(entries)

        return dict(
            tracker=tracker,
            bugs=bugs,
            charts_data=json.dumps(burndown),
            piechart_data=piechart_data,
            info=sw.get_info(),
            sprint_tabs=sw.get_tabs()
        )


@view_config(route_name='scrum_sprint_retros', permission='can_view_sprints')
class Retros(ClientProtectionMixin, FetchBugsMixin, BaseSprintView):
    def get(self):
        sprint = self.v['sprint']
        bugs = self._fetch_bugs(sprint)
        sw = SprintWrapper(sprint, bugs, self.request)

        sprints = DBSession.query(Sprint) \
                             .filter(Sprint.project_id==sprint.project_id) \
                             .order_by(Sprint.start.desc())

        return dict(
            bugs=bugs,
            info=sw.get_info(),
            sprints=sprints,
            sprint_tabs=sw.get_tabs()
        )


@view_config(route_name='scrum_sprint_edit', permission='can_edit_sprints')
class Edit(BaseView):
    def dispatch(self):
        sprint_id = self.request.GET.get('sprint_id')
        sprint = Sprint.query.get(sprint_id)
        form = SprintForm(self.request.POST, obj=sprint)
        if self.request.method == 'POST' and form.validate():
            project_id = form.project_id.data
            project = Project.query.get(project_id)
            sprint.name = form.name.data
            sprint.client_id = project.client_id
            sprint.project_id = project.id
            sprint.team_id = form.team_id.data or None
            sprint.bugs_project_ids = map(int, form.bugs_project_ids.data)
            sprint.start = form.start.data
            sprint.end = form.end.data
            sprint.goal = form.goal.data
            sprint.board = form.board.data
            sprint.retrospective_note = form.retrospective_note.data
            DBSession.add(sprint)
            self.flash(self._(u"Sprint edited"))
            LOG(u"Sprint edited")
            if self.request.POST.get('save-and-go'):
                url = self.request.url_for('/scrum/sprint/board', sprint_id=sprint.id)
            else:
                url = self.request.url_for('/scrum/sprint/edit', sprint_id=sprint.id)
            return HTTPFound(location=url)
        return dict(
            form=form,
            sprint=sprint
        )


@view_config(route_name='scrum_sprint_add', permission='can_edit_sprints')
class Add(BaseView):
    def dispatch(self):
        form = SprintForm(self.request.POST)
        if self.request.method == 'POST' and form.validate():
            project = Project.query.get(int(form.project_id.data))
            sprint = Sprint(
                name=form.name.data,
                client_id=project.client_id,
                project_id=project.id,
                team_id=form.team_id.data or None,
                bugs_project_ids = map(int, form.bugs_project_ids.data),
                start=form.start.data,
                end=form.end.data,
                board=form.board.data,
                goal=form.goal.data,
                retrospective_note = form.retrospective_note.data,
            )
            DBSession.add(sprint)
            DBSession.flush()
            self.flash(self._(u"New sprint added"))
            LOG(u"Sprint added")
            url = self.request.url_for('/scrum/sprint/show', sprint_id=sprint.id)
            return HTTPFound(location=url)
        return dict(
            form=form,
        )


@view_config(route_name='scrum_sprint_delete', renderer='intranet3:templates/common/delete.html', permission='can_edit_sprints')
class Delete(BaseView):

    def dispatch(self):
        sprint_id = self.request.GET.get('sprint_id')
        sprint =  Sprint.query.get(sprint_id)
        form = DeleteForm(self.request.POST)
        if self.request.method == 'POST' and form.validate():
            DBSession.delete(sprint)
            back_url = self.request.url_for('/scrum/sprint/list')
            return HTTPFound(location=back_url)
        return dict(
            type_name=u'sprint',
            title=u'%s' % sprint.name,
            url=self.request.url_for('/scrum/sprint/delete', sprint_id=sprint.id),
            back_url=self.request.url_for('/scrum/sprint/list'),
            form=form
        )

@view_config(route_name='scrum_sprint_team', permission='can_view_sprints')
class Team(ClientProtectionMixin, FetchBugsMixin, BaseSprintView):
    def get(self):
        sprint = self.v['sprint']
        bugs = self._fetch_bugs(sprint)
        sw = SprintWrapper(sprint, bugs, self.request)

        return dict(
            sprint=sprint,
            info=sw.get_info(),

        )

@view_config(route_name='scrum_sprint_extra-tab', permission='can_view_sprints')
class ExtraTab(ClientProtectionMixin, FetchBugsMixin, BaseSprintView):
    def get(self):
        sprint = self.v['sprint']
        bugs = self._fetch_bugs(sprint)
        sw = SprintWrapper(sprint, bugs, self.request)

        tab_name = self.request.GET['tab_name']
        tabs = sw.get_tabs()

        extra_tab = dict(
            name=tab_name,
            link=dict(tabs)[tab_name]
        )
        return dict(
            info=sw.get_info(),
            sprint_tabs=tabs,
            extra_tab=extra_tab,
        )
