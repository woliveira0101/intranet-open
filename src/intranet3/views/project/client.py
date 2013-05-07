from __future__ import with_statement
import copy
import datetime

import markdown
from pyramid.view import view_config
from pyramid.response import Response
from pyramid.httpexceptions import HTTPBadRequest, HTTPForbidden, HTTPNotFound

from intranet3.models import Project, Sprint
from intranet3.utils.views import BaseView
from intranet3.log import INFO_LOG, WARN_LOG, ERROR_LOG, DEBUG_LOG, EXCEPTION_LOG
from intranet3.lib.times import TimesReportMixin, Row
from intranet3.lib.scrum import get_velocity_chart_data
from intranet3.forms.times import ProjectTimeForm
from intranet3.forms.scrum import SprintListFilterForm
from intranet3.views.bugs import EveryonesProject

LOG = INFO_LOG(__name__)
WARN = WARN_LOG(__name__)
ERROR = ERROR_LOG(__name__)
DEBUG = DEBUG_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)


MAX_TIMEOUT = 20 # DON'T WAIT LONGER THAN DEFINED TIMEOUT
MAX_TICKETS_PER_REQUEST = 50 # max number of ticket ids to include in a single request to tracker

@view_config(route_name='project_client_times', permission='client')
class Times(TimesReportMixin, BaseView):
    def dispatch(self):
        client = self.request.user.get_client()
        form = ProjectTimeForm(self.request.GET, client=client)

        GET = self.request.GET
        if len(GET) == 1 and 'group_by_bugs' not in GET and 'group_by_user' not in GET:
            # ugly hack
            form.group_by_bugs.data = True
            form.group_by_user.data = True

        projects = form.projects.data
        if len(projects) != 1 or not projects[0].isdigit():
            raise HTTPBadRequest
        project = Project.query.get(projects[0])
        if not project:
            raise HTTPBadRequest

        if not form.validate():
            return dict(form=form, project=project)

        start_date, end_date = form.date_range.data
        without_bug_only = form.without_bug_only.data
        group_by = True, True, form.group_by_bugs.data, form.group_by_user.data

        LOG(u'Tickets project report %r - %r' % (start_date, end_date))

        uber_query = self._prepare_uber_query(
            start_date, end_date, projects, [], without_bug_only,
        )

        entries = uber_query.all()
        entries_sum = sum([e[-1] for e in entries])

        participation_of_workers = self._get_participation_of_workers(entries)

        tickets_id = ','.join([str(e[2]) for e in entries])
        trackers_id = ','.join([str(e[4].id) for e in entries])

        rows = Row.from_ordered_data(entries, group_by)

        return dict(
            rows=rows,
            entries_sum=entries_sum,
            form=form,
            project=project,
            participation_of_workers=participation_of_workers,
            participation_of_workers_sum=sum([time[1] for time in participation_of_workers]),
            trackers_id=trackers_id, tickets_id=tickets_id,
        )


@view_config(route_name='project_client_sprints', permission='client')
class Sprints(BaseView):
    def get(self):
        client = self.request.user.get_client()

        form = SprintListFilterForm(self.request.GET, client=client)
        active_only = form.active_only.data
        limit = form.limit.data or 10

        sprints = Sprint.query.order_by(Sprint.modified)

        if client:
            sprints = sprints.filter(Sprint.client_id == client.id)
        if form.project_id.data and form.project_id.data != 'None':
            project_id = int(form.project_id.data)
            project = Project.query.get(project_id)
            sprints = sprints.filter(Sprint.project_id == project_id)
        else:
            raise HTTPBadRequest

        all_sprints = copy.copy(sprints)
        velocity_chart_data = get_velocity_chart_data(all_sprints)

        if active_only:
            sprints = sprints.filter(Sprint.end >= datetime.date.today())

        if limit:
            sprints.limit(limit)

        sprints = sprints.all()

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
            project=project,
            velocity_chart_data=velocity_chart_data,
            stats=stats,
        )


@view_config(route_name='project_client_backlog', permission='client')
class Backlog(EveryonesProject):
    def protect(self):
        project_id = self.request.GET.get('project_id')
        if not project_id or not project_id.isdigit():
            raise HTTPBadRequest

        client = self.request.user.get_client()
        if client:
            project = Project.query.get(project_id)
            if client.id != project.client_id:
                raise HTTPForbidden


@view_config(route_name='project_client_field', permission='client')
class ProjectField(BaseView):
    def protect(self):
        project_id = self.request.GET.get('project_id')
        if not project_id or not project_id.isdigit():
            raise HTTPBadRequest

        client = self.request.user.get_client()
        project = Project.query.get(project_id)
        if client:
            if client.id != project.client_id:
                raise HTTPForbidden

        self.v['client'] = client
        self.v['project'] = project


    def get(self):
        project_field = self.request.GET.get('field')
        if project_field == 'definition_of_done':
            result = self.v['project'].definition_of_done
            header = 'Definition of Done'
        elif project_field == 'working_agreement':
            result = self.v['project'].working_agreement
            header = 'Working agreement'
        else:
            raise HTTPNotFound
        md = markdown.Markdown()
        result = md.convert(result)
        result = '<h2 class="content-header">%s</h2>%s' % (header, result)
        return Response(result)



