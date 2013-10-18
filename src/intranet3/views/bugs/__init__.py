from functools import partial
from collections import defaultdict

from pyramid.view import view_config

from intranet3.utils.views import BaseView
from intranet3 import models as m
from intranet3.lib.bugs import Bugs
from intranet3 import helpers as h

class FilterMixin(object):
    def _get_params(self):
        resolved = 1 if self.request.GET.get('resolved') == '1' else 0
        show_all_bugs = 1 if self.request.GET.get('all_bugs') == '1' else 0
        show_all_projects = 1 if self.request.GET.get('all_projects') == '1' else 0
        sort_by_date = 1 if self.request.GET.get('sort_by_date') == '1' else 0
        return resolved, show_all_bugs, show_all_projects, sort_by_date

class GroupedBugsMixin(object):
        def get_all(self, resolved, all_projects=True):
            bugs = Bugs(self.request).get_all(resolved)
            people = m.User.query.order_by(m.User.freelancer, m.User.name)\
                                .filter(m.User.is_not_client())\
                                .filter(m.User.is_active==True)\
                                .all()

            entries = self.session.query(m.Client, m.Project)\
                                  .filter(m.Client.id == m.Project.client_id)\
                                  .filter(m.Project.tracker_id == m.Tracker.id)\
                                  .order_by(m.Client.name, m.Project.name)

            grouped = defaultdict(lambda: defaultdict(lambda: 0))
            client_sums = defaultdict(lambda: 0)
            project_sums = defaultdict(lambda: 0)
            people_sums = defaultdict(lambda: 0)
            total = 0

            for bug in bugs:
                project = bug.project.id if bug.project else None
                client = bug.project.client_id if bug.project else None

                user = bug.reporter if resolved else bug.owner
                client_sums[client] += 1
                project_sums[project] += 1
                people_sums[user.id] += 1
                grouped[project][user.id] += 1
                total += 1

            def client_filter(client, project):
                """
                Filter out projects that don't belongs to client
                and
                filter out projects without bugs unless all_project is set to True/1
                """
                if self.request.is_user_in_group('client'):
                    if client.id == self.request.user.client.id:
                        return project if project_sums[project.id] or all_projects else None
                else:
                    return project if project_sums[project.id] or all_projects else None


            clients = h.groupby(entries, lambda x: x[0], lambda x: client_filter(x[0], x[1]))


            all_people = not self.request.is_user_in_group('client')

            ## for client show only employees with bugs
            people = [ person for person in people if people_sums[person.id] or all_people ]

            return bugs, grouped, people, people_sums, client_sums, project_sums, total, clients


@view_config(route_name='my_bugs', permission='bugs_owner')
class My(BaseView):
    """
    Lists bugs for given user.
    Bugs are fetched from all trackers that the user configured credentials to
    """

    def get(self):
        resolved = int(self.request.GET.get('resolved', 0))
        return dict(
            bugs=[],
            resolved=resolved,
            url = self.request.url_for('/bugs/my_json', resolved=resolved),
        )

@view_config(route_name='my_bugs_json', renderer='intranet3:templates/bugs/_list.html', permission='bugs_owner')
class MyJson(BaseView):
    """
    Lists bugs for given user.
    Bugs are fetched from all trackers that the user configured credentials to
    """

    def get(self):
        resolved = int(self.request.GET.get('resolved', 0))
        bugs = Bugs(self.request).get_user(resolved)
        bugs = sorted(bugs, cmp=h.sorting_by_severity)
        return dict(bugs=bugs)


@view_config(route_name='bug_report', permission='task_pivot')
class Report(GroupedBugsMixin, FilterMixin, BaseView):

    def get(self):
        resolved, show_all_bugs, show_all_projects, sort_by_date = self._get_params()
        bugs, grouped, people, people_sums, client_sums, project_sums, total, clients = self.get_all(resolved, show_all_projects)
        if not sort_by_date:
            bugs = sorted(bugs, cmp=h.sorting_by_severity)
        else:
            bugs = sorted(bugs, key=lambda b: b.opendate.replace(tzinfo=None))

        return dict(
            bugs=grouped, people=people,
            people_sums=people_sums, project_sums=project_sums, total=total,
            all_bugs=bugs, clients=clients, client_sums=client_sums,
            url_constructor=partial(self.request.url_for, '/bugs/report'),
            resolved=resolved, show_all_projects=show_all_projects,
            show_all_bugs=show_all_bugs,
            sort_by_date=sort_by_date
        )



@view_config(route_name='bugs_user', renderer='intranet3:templates/bugs/_filtered_report.html', permission='client')
class User(GroupedBugsMixin, FilterMixin, BaseView):
    """ Show bugs for given user """
    def get(self):
        user_id = self.request.GET.get('user_id')
        user = m.User.query.get(user_id)
        resolved, show_all_bugs, show_all_projects, sort_by_date = self._get_params()
        bugs, grouped, people, people_sums, client_sums, project_sums, total, clients = self.get_all(resolved, show_all_projects)
        comparator = (lambda bug: bug.reporter.id == user.id) if resolved else (lambda bug: bug.owner.id == user.id)
        bugs = [bug for bug in bugs if comparator(bug)]
        if not sort_by_date:
            bugs = sorted(bugs, cmp=h.sorting_by_severity)
        else:
            bugs = sorted(bugs, key=lambda b: b.opendate.replace(tzinfo=None))
        return dict(
            bugs=bugs, grouped=grouped, people=people, client_sums=client_sums,
            people_sums=people_sums, project_sums=project_sums, total=total,
            title=self._(u"Bugs of user ${email}", email=user.email), clients=clients,
            url_constructor=partial(self.request.url_for, '/bugs/user', user_id=user.id),
            resolved=resolved, show_all_projects=show_all_projects,
            sort_by_date=sort_by_date
        )


@view_config(route_name='bugs_project_user', renderer='intranet3:templates/bugs/_filtered_report.html', permission='client')
class ProjectUser(GroupedBugsMixin, FilterMixin, BaseView):
    def get(self):
        user_id = self.request.GET.get('user_id')
        project_id = self.request.GET.get('project_id')
        user = m.User.query.get(user_id)
        project = m.Project.query.get(project_id)

        resolved, show_all_bugs, show_all_projects, sort_by_date = self._get_params()
        bugs, grouped, people, people_sums, client_sums, project_sums, total, clients = self.get_all(resolved, show_all_projects)
        user = m.User.query.get(user_id)
        comparator = (lambda bug: bug.reporter.id == user.id) if resolved else (lambda bug: bug.owner.id == user.id)
        bugs = [bug for bug in bugs if (bug.project and bug.project.id == project.id and comparator(bug))]
        if not sort_by_date:
            bugs = sorted(bugs, cmp=h.sorting_by_severity)
        else:
            bugs = sorted(bugs, key=lambda b: b.opendate.replace(tzinfo=None))


        title=self._(u"Bugs of user ${email} for project ${client_name} / ${project_name}",
            email=user.email,
            client_name=project.client.name,
            project_name=project.name,
        )

        return dict(
            bugs=bugs, grouped=grouped, clients=clients, people=people, client_sums=client_sums,
            people_sums=people_sums, project_sums=project_sums, total=total,
            title=title,
            url_constructor=partial(self.request.url_for, '/bugs/project_user', project_id=project.id, user_id=user_id),
            resolved=resolved, show_all_projects=show_all_projects,
            sort_by_date=sort_by_date
        )


@view_config(route_name='bugs_project', renderer='intranet3:templates/bugs/_filtered_report.html', permission='client')
class Project(GroupedBugsMixin, FilterMixin, BaseView):
    """ Show bugs for a project """
    def get(self):
        project_id = self.request.GET.get('project_id')
        project = m.Project.query.get(project_id)

        resolved, show_all_bugs, show_all_projects, sort_by_date = self._get_params()

        bugs, grouped, people, people_sums, client_sums, project_sums, total, clients = self.get_all(resolved, show_all_projects)
        key = project.id
        bugs = [bug for bug in bugs if (bug.project and bug.project.id == key)]
        if not sort_by_date:
            bugs = sorted(bugs, cmp=h.sorting_by_severity)
        else:
            bugs = sorted(bugs, key=lambda b: b.opendate.replace(tzinfo=None))
        return dict(
            bugs=bugs, grouped=grouped, clients=clients, people=people, client_sums=client_sums,
            people_sums=people_sums, project_sums=project_sums, total=total,
            title=self._(u"Bugs for project ${client} / ${project}", client=project.client.name, project=project.name),
            url_constructor=partial(self.request.url_for, '/bugs/project', project_id=project.id),
            resolved=resolved, show_all_projects=show_all_projects,
            sort_by_date=sort_by_date
        )


@view_config(route_name='bugs_client', renderer='intranet3:templates/bugs/_filtered_report.html', permission='client')
class Client(GroupedBugsMixin, FilterMixin, BaseView):
    """ Show bugs for a client """
    def get(self):
        client_id = self.request.GET.get('client_id')
        client = m.Client.query.get(client_id)

        resolved, show_all_bugs, show_all_projects, sort_by_date = self._get_params()

        bugs, grouped, people, people_sums, client_sums, project_sums, total, clients = self.get_all(resolved, show_all_projects)
        key = client.id
        bugs = [bug for bug in bugs if (bug.project and bug.project.client and bug.project.client.id == key)]
        if not sort_by_date:
            bugs = sorted(bugs, cmp=h.sorting_by_severity)
        else:
            bugs = sorted(bugs, key=lambda b: b.opendate.replace(tzinfo=None))

        return dict(
            bugs=bugs, grouped=grouped, clients=clients, people=people, client_sums=client_sums,
            people_sums=people_sums, project_sums=project_sums, total=total,
            title=self._(u"Bugs for client ${client}", client=client.name),
            url_constructor=partial(self.request.url_for, '/bugs/client', client_id=client.id),
            resolved=resolved, show_all_projects=show_all_projects,
            sort_by_date=sort_by_date
        )


@view_config(route_name='bugs_other_project_user', renderer='intranet3:templates/bugs/_filtered_report.html', permission='client')
class OtherProjectsUser(GroupedBugsMixin, FilterMixin, BaseView):
    """ Show other bugs"""
    def get(self):
        user_id = self.request.GET.get('user_id')
        user = m.User.query.get(user_id)
        resolved, show_all_bugs, show_all_projects, sort_by_date = self._get_params()

        bugs, grouped, people, people_sums, client_sums, project_sums, total, clients = self.get_all(resolved, show_all_projects)
        comparator = (lambda bug: bug.reporter.id == user.id) if resolved else (lambda bug: bug.owner.id == user.id)
        bugs = [bug for bug in bugs if (not bug.project and comparator(bug))]
        bugs = sorted(bugs, cmp=h.sorting_by_severity)
        return dict(
            bugs=bugs, grouped=grouped, clients=clients, people=people, client_sums=client_sums,
            people_sums=people_sums, project_sums=project_sums, total=total,
            title=self._(u"Other projects bugs for user ${email}", email=user.email),
            url_constructor=partial(self.request.url_for, '/bugs/other_projects_user', id=user.id),
            resolved=resolved, show_all_projects=show_all_projects
        )



@view_config(route_name='bugs_other_project', renderer='intranet3:templates/bugs/_filtered_report.html')
class OtherProjects(GroupedBugsMixin, FilterMixin, BaseView):
    """ Show other bugs"""
    def get(self):
        resolved, show_all_bugs, show_all_projects, sort_by_date = self._get_params()

        bugs, grouped, people, people_sums, client_sums, project_sums, total, clients = self.get_all(resolved, show_all_projects)
        bugs = [bug for bug in bugs if not bug.project]
        bugs = sorted(bugs, cmp=h.sorting_by_severity)
        return dict(
            bugs=bugs, grouped=grouped, clients=clients, people=people, client_sums=client_sums,
            people_sums=people_sums, project_sums=project_sums, total=total,
            title=self._(u"List of bugs all users in other projects"),
            url_constructor=partial(self.request.url_for, '/bugs/other_projects'),
            resolved=resolved, show_all_projects=show_all_projects
        )


@view_config(route_name='everyones_bugs', permission='projects')
class Everyones(FilterMixin, BaseView):
    def get(self):
        resolved, show_all_bugs, show_all_projects, sort_by_date = self._get_params()
        projects = self.session.query(m.Client, m.Project).filter(m.Client.id==m.Project.client_id).order_by(m.Client.name, m.Project.name)
        return dict(projects=projects, resolved=resolved)


@view_config(route_name='bugs_everyones_project', permission='projects')
class EveryonesProject(FilterMixin, BaseView):
    """ Show bugs on everyone in a given project """
    def get(self):
        project_id = self.request.GET.get('project_id')
        project = m.Project.query.get(project_id)

        resolved, show_all_bugs, show_all_projects, sort_by_date = self._get_params()

        projects = self.session.query(m.Client, m.Project).filter(m.Client.id==m.Project.client_id).order_by(m.Client.name, m.Project.name)
        tracker = project.tracker
        bugs = Bugs(self.request).get_project(project, resolved)
        if bugs:
            # will not be able to fetch, because user does not have credentials for this tracker
            bugs = sorted(bugs, cmp=h.sorting_by_severity)
            return dict(unable=False, bugs=bugs, projects=projects, project=project, tracker=tracker, resolved=resolved)
        else:
            # fetch is possible
            return dict(unable=True, projects=projects, project=project, tracker=tracker, resolved=resolved)

