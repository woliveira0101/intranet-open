from __future__ import with_statement

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPForbidden
from sqlalchemy.orm.query import aliased

from intranet3.forms.common import DeleteForm
from intranet3.utils.views import BaseView
from intranet3.models import Tracker, TrackerCredentials, Project
from intranet3.forms.tracker import (TrackerForm, TRACKER_TYPES, TrackerLoginForm,
                                     trackers_login_validators)
from intranet3.log import INFO_LOG

LOG = INFO_LOG(__name__)

class UserCredentialsMixin(object):
    def _get_current_users_credentials(self):
        creds = aliased(
            TrackerCredentials,
            TrackerCredentials.query.filter(TrackerCredentials.user_id==self.request.user.id).subquery()
        )
        query = self.session.query(
            Tracker,
            creds
        ).outerjoin((creds, Tracker.credentials))
        if self.request.user.client:
            client = self.request.user.client
            query = query.filter(Project.tracker_id==Tracker.id).filter(Project.client_id==client.id)

        return [
            {"tracker": tracker, "has_creds": bool(credentials), "creds": credentials}
            for tracker, credentials in query
        ]

    def _get_current_users_credentials_for_tracker(self, tracker):
        if self.request.user.client:
            client = self.request.user.client
            query = Tracker.query.filter(Project.tracker_id==tracker.id)\
                                 .filter(Project.client_id==client.id)\
                                 .filter(Tracker.id==Project.tracker_id)
            result = query.first()
            if not result:
                raise HTTPForbidden

        return TrackerCredentials.query.filter(TrackerCredentials.user==self.request.user)\
                                       .filter(TrackerCredentials.tracker_id==tracker.id).first()


@view_config(route_name='tracker_list', permission='bugs_owner')
class List(UserCredentialsMixin, BaseView):
    def get(self):
        trackers = self._get_current_users_credentials()
        return dict(trackers=trackers)


@view_config(route_name='tracker_view', permission='admin')
class View(BaseView):
    def get(self):
        tracker_id = self.request.GET.get('tracker_id')
        tracker = Tracker.query.get(tracker_id)
        return dict(tracker=tracker, TRACKER_TYPES=TRACKER_TYPES)


@view_config(route_name='tracker_add', permission='admin')
class Add(BaseView):
    def get(self):
        form = TrackerForm()
        return dict(form=form)

    def post(self):
        form = TrackerForm(self.request.POST)
        if form.validate():
            tracker = Tracker(
                type=form.type.data,
                name=form.name.data,
                url=form.url.data,
                mailer=form.mailer.data
            )
            self.session.add(tracker)
            self.flash(self._(u"New tracker added"))
            LOG(u"Tracker added")
            url = self.request.url_for('/tracker/list')
            return HTTPFound(location=url)
        return dict(form=form)


def _add_tracker_login_validator(tracker_name, form):
    validators = {}
    for tracker_name in (tracker_name, 'all'):
        if tracker_name in trackers_login_validators:
            for validator_name, validator in trackers_login_validators[tracker_name].items():
                if validator_name not in validators:
                    validators[validator_name] = []

                validators[validator_name].append(validator)

    for validator_name, validator in validators.items():
        getattr(form, validator_name).validators = validators[validator_name]

@view_config(route_name='tracker_login', permission='bugs_owner')
class Login(UserCredentialsMixin, BaseView):
    def get(self):
        tracker_id = self.request.GET.get('tracker_id')
        tracker =  Tracker.query.get(tracker_id)
        credentials = self._get_current_users_credentials_for_tracker(tracker)
        form = TrackerLoginForm(obj=credentials)
        return dict(form=form, tracker=tracker)

    def post(self):
        tracker_id = self.request.GET.get('tracker_id')
        tracker =  Tracker.query.get(tracker_id)
        credentials = self._get_current_users_credentials_for_tracker(tracker)
        form = TrackerLoginForm(self.request.POST, obj=credentials)

        _add_tracker_login_validator(tracker.name, form)

        if form.validate():
            if credentials is None:
                credentials = TrackerCredentials(
                    user_id=self.request.user.id,
                    tracker_id=tracker.id,
                    login=form.login.data,
                    password=form.password.data,
                )
                self.session.add(credentials)
            else:
                credentials.login=form.login.data
                credentials.password=form.password.data
            self.flash(self._(u"Credentials saved"))
            LOG(u"Credentials saved")
            url = self.request.url_for('/tracker/list')
            return HTTPFound(location=url)
        return dict(form=form, tracker=tracker)

@view_config(route_name='tracker_edit', permission='admin')
class Edit(BaseView):
    def get(self):
        tracker_id = self.request.GET.get('tracker_id')
        tracker =  Tracker.query.get(tracker_id)
        form = TrackerForm(obj=tracker)
        return dict(tracker_id=tracker.id, form=form)

    def post(self):
        tracker_id = self.request.GET.get('tracker_id')
        tracker =  Tracker.query.get(tracker_id)
        form = TrackerForm(self.request.POST, obj=tracker)
        if form.validate():
            tracker.type = form.type.data
            tracker.name = form.name.data
            tracker.url = form.url.data
            tracker.mailer = form.mailer.data
            self.flash(self._(u"Tracker saved"))
            LOG(u"Tracker saved")
            url = self.request.url_for('/tracker/list')
            return HTTPFound(location=url)
        return dict(tracker_id=tracker.id, form=form)



@view_config(route_name='tracker_delete',
             renderer='intranet3:templates/common/delete.html',
             permission='admin')
class Delete(BaseView):

    def dispatch(self):
        tracker_id = self.request.GET.get('tracker_id')
        tracker =  Tracker.query.get(tracker_id)
        form = DeleteForm(self.request.POST)
        if self.request.method == 'POST' and form.validate():
            tracker.credentials.delete()
            tracker.projects.delete()
            self.session.delete(tracker)
            back_url = self.request.url_for('/tracker/list')
            return HTTPFound(location=back_url)
        return dict(
            type_name=u'tracker',
            title=u'%s' % tracker.name,
            url=self.request.url_for('/tracker/delete', tracker_id=tracker.id),
            back_url=self.request.url_for('/tracker/list'),
            form=form
        )


@view_config(route_name='tracker_delete_login',
             renderer='intranet3:templates/common/delete.html',
             permission='bugs_owner')
class DeleteLogin(BaseView):
    def dispatch(self):
        tracker_id = self.request.GET.get('tracker_id')
        tracker =  Tracker.query.get(tracker_id)
        form = DeleteForm(self.request.POST)
        if self.request.method == 'POST' and form.validate():
            credentials = tracker.credentials.filter(TrackerCredentials.user_id==self.request.user.id).one()
            self.session.delete(credentials)
            back_url = self.request.url_for('/tracker/list')
            return HTTPFound(location=back_url)
        return dict(
            type_name=u'tracker',
            title=self._(u'Credentials for user ${name} on tracker ${tracker}', name=self.request.user.name, tracker=tracker.name),
            url=self.request.url_for('/tracker/delete_login', tracker_id=tracker.id),
            back_url=self.request.url_for('/tracker/list'),
            form=form
        )
