# -*- coding: utf-8 -*-
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound

from intranet3.utils.views import BaseView
from intranet3.models import Client, Project
from intranet3.log import INFO_LOG
from intranet3.forms.project import ProjectForm
from intranet3.forms.common import DeleteForm
from intranet3.models.project import SelectorMapping

LOG = INFO_LOG(__name__)


@view_config(route_name='project_view', permission='view_projects')
class View(BaseView):
    def get(self):
        project_id = self.request.GET.get('project_id')
        project =  Project.query.get(project_id)
        return dict(project=project)


@view_config(route_name='project_add', permission='edit_projects')
class Add(BaseView):
    def dispatch(self):
        client_id = self.request.GET.get('client_id')
        client = Client.query.get(client_id)
        form = ProjectForm(self.request.POST)
        if self.request.method == 'POST' and form.validate():
            tracker_id = form.tracker_id.data
            coordinator_id = int(form.coordinator_id.data) if form.coordinator_id.data.isdigit() else None
            project = Project(
                client=client,
                name=form.name.data,
                coordinator_id=coordinator_id,
                tracker_id=tracker_id,
                turn_off_selectors=form.turn_off_selectors.data,
                project_selector=form.project_selector.data,
                component_selector=form.component_selector.data,
                version_selector=form.version_selector.data,
                ticket_id_selector=form.ticket_id_selector.data,
                active=form.active.data,
                google_card=form.google_card.data,
                google_wiki=form.google_wiki.data,
                mailing_url=form.mailing_url.data,
                working_agreement=form.working_agreement.data,
                definition_of_done=form.definition_of_done.data,
                definition_of_ready=form.definition_of_ready.data,
                continuous_integration_url=form.continuous_integration_url.data,
                backlog_url=form.backlog_url.data,
                status = form.status.data,
            )
            self.session.add(project)
            self.session.flush()
            self.flash(self._(u"Project added"))
            LOG(u"Project added")
            SelectorMapping.invalidate_for(tracker_id)
            return HTTPFound(location=self.request.url_for('/client/view', client_id=project.client_id))
        return dict(client=client, form=form)

@view_config(route_name='project_edit', permission='edit_sprints')
class Edit(BaseView):
    def dispatch(self):
        project_id = self.request.GET.get('project_id')
        project =  self.session.query(Project).filter(Project.id==project_id).one()
        form = ProjectForm(self.request.POST, obj=project)
        # hack, when user has no permision edit_projects (that means that he has only scrum perms)
        # we do not validate the form
        if self.request.method == 'POST' and (not self.request.has_perm('edit_projects') or form.validate()):
            project.working_agreement = form.working_agreement.data
            project.definition_of_done = form.definition_of_done.data
            project.definition_of_ready = form.definition_of_ready.data
            project.continuous_integration_url = form.continuous_integration_url.data
            project.backlog_url = form.backlog_url.data
            project.status = form.status.data
            project.sprint_tabs = form.sprint_tabs.data
            if self.request.has_perm('edit_projects'):
                project.name = form.name.data
                coordinator_id = int(form.coordinator_id.data) if form.coordinator_id.data.isdigit() else None
                project.coordinator_id = coordinator_id
                project.tracker_id = form.tracker_id.data
                project.turn_off_selectors = form.turn_off_selectors.data
                project.project_selector = form.project_selector.data
                project.component_selector = form.component_selector.data
                project.version_selector = form.version_selector.data
                project.ticket_id_selector = form.ticket_id_selector.data
                project.active = form.active.data
                project.google_card = form.google_card.data
                project.google_wiki = form.google_wiki.data
                project.mailing_url = form.mailing_url.data
                project.status = form.status.data

            self.flash(self._(u"Project saved"))
            LOG(u"Project saved")
            SelectorMapping.invalidate_for(project.tracker_id)
            return HTTPFound(location=self.request.url_for('/project/edit', project_id=project.id))
        return dict(project_id=project.id, form=form)


@view_config(route_name='project_delete', renderer='intranet3:templates/common/delete.html', permission='delete_projects')
class Delete(BaseView):
    def dispatch(self):
        project_id = self.request.GET.get('project_id')
        project =  Project.query.get(project_id)
        form = DeleteForm(self.request.POST)
        back_url = self.request.url_for('/client/view', client_id=project.client_id)
        if self.request.method == 'POST' and form.validate():
            self.session.delete(project)
            SelectorMapping.invalidate_for(project.tracker_id)
            return HTTPFound(location=back_url)
        return dict(
            type_name=u'project',
            title=project.name,
            url=self.request.url_for('/project/delete', project_id=project.id),
            back_url=back_url,
            form=form
        )
