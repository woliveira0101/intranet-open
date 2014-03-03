from __future__ import with_statement

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPForbidden
from sqlalchemy.orm.query import aliased

from intranet3.forms.common import DeleteForm
from intranet3.utils.views import BaseView
from intranet3.models import Tracker, TrackerCredentials, Project, DBSession
from intranet3.forms.tracker import (
    TrackerForm,
    TRACKER_TYPES,
    TrackerLoginForm,
    trackers_login_validators,
)
from intranet3.log import INFO_LOG
from intranet3.asyncfetchers import (
    get_fetcher,
    FetcherBaseException,
    FetcherTimeout,
    FetcherBadDataError,
)

LOG = INFO_LOG(__name__)


class UserCredentialsMixin(object):
    def _get_current_users_credentials(self):
        creds = aliased(
            TrackerCredentials,
            TrackerCredentials.query.filter(TrackerCredentials.user_id==self.request.user.id).subquery()
        )
        query = DBSession.query(
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


@view_config(route_name='tracker_list', permission='can_see_own_bugs')
class List(UserCredentialsMixin, BaseView):
    def get(self):
        trackers = self._get_current_users_credentials()
        return dict(trackers=trackers)


@view_config(route_name='tracker_view', permission='can_edit_trackers')
class View(BaseView):
    def get(self):
        tracker_id = self.request.GET.get('tracker_id')
        tracker = Tracker.query.get(tracker_id)
        return dict(tracker=tracker, TRACKER_TYPES=TRACKER_TYPES)


@view_config(route_name='tracker_add', permission='can_edit_trackers')
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
                mailer=form.mailer.data,
                description=form.description.data,
            )
            DBSession.add(tracker)
            self.flash(self._(u"New tracker added"))
            LOG(u"Tracker added")
            url = self.request.url_for('/tracker/list')
            return HTTPFound(location=url)
        return dict(form=form)


@view_config(route_name='tracker_login', permission='can_see_own_bugs')
class Login(UserCredentialsMixin, BaseView):
    def dispatch(self):
        tracker_id = self.request.GET.get('tracker_id')
        tracker = Tracker.query.get(tracker_id)
        form_class = tracker.get_form()

        try:
            form = form_class(tracker, self.request.user, self.request.POST)
        except Tracker.TrackerPermissionError as e:
            raise HTTPForbidden(e)

        if self.request.method == 'POST':
            if form.validate():
                credentials = form.save_credentials()
                self.flash(self._(u"Credentials saved"))

                fetcher = tracker.get_fetcher(credentials, self.request.user)

                if self._check_tracker_connection(fetcher):
                    url = self.request.url_for('/tracker/list')
                    return HTTPFound(location=url)

        return dict(form=form, tracker=tracker)

    def _check_tracker_connection(self, fetcher):
        try:
            fetcher.fetch_user_tickets()
            fetcher.clear_user_cache()
            fetcher.get_result()

        except FetcherTimeout as e:
            self.flash(
                'Fetchers for trackers %s timed-out' %
                fetcher.tracker.name,
                klass='error',
            )
            return False

        except FetcherBadDataError as e:
            self.flash(e, klass='error')
            return False

        except FetcherBaseException as e:
            self.flash(
                'Could not fetch bugs from tracker %s' %
                fetcher.tracker.name,
                klass='error',
            )
            return False

        else:
            return True


@view_config(route_name='tracker_edit', permission='can_edit_trackers')
class Edit(BaseView):
    def get(self):
        tracker_id = self.request.GET.get('tracker_id')
        tracker = Tracker.query.get(tracker_id)
        form = TrackerForm(obj=tracker)
        return dict(tracker_id=tracker.id, form=form)

    def post(self):
        tracker_id = self.request.GET.get('tracker_id')
        tracker = Tracker.query.get(tracker_id)
        form = TrackerForm(self.request.POST, obj=tracker)
        if form.validate():
            tracker.type = form.type.data
            tracker.name = form.name.data
            tracker.url = form.url.data
            tracker.mailer = form.mailer.data
            tracker.description = form.description.data
            self.flash(self._(u"Tracker saved"))
            LOG(u"Tracker saved")
            url = self.request.url_for('/tracker/list')
            return HTTPFound(location=url)
        return dict(tracker_id=tracker.id, form=form)


@view_config(route_name='tracker_delete', renderer='intranet3:templates/common/delete.html', permission='can_edit_trackers')
class Delete(BaseView):

    def dispatch(self):
        tracker_id = self.request.GET.get('tracker_id')
        tracker =  Tracker.query.get(tracker_id)
        form = DeleteForm(self.request.POST)
        if self.request.method == 'POST' and form.validate():
            tracker.credentials.delete()
            tracker.projects.delete()
            DBSession.delete(tracker)
            back_url = self.request.url_for('/tracker/list')
            return HTTPFound(location=back_url)
        return dict(
            type_name=u'tracker',
            title=u'%s' % tracker.name,
            url=self.request.url_for('/tracker/delete', tracker_id=tracker.id),
            back_url=self.request.url_for('/tracker/list'),
            form=form
        )


@view_config(route_name='tracker_delete_login', renderer='intranet3:templates/common/delete.html', permission='can_see_own_bugs')
class DeleteLogin(BaseView):
    def dispatch(self):
        tracker_id = self.request.GET.get('tracker_id')
        tracker =  Tracker.query.get(tracker_id)
        form = DeleteForm(self.request.POST)
        if self.request.method == 'POST' and form.validate():
            credentials = tracker.credentials.filter(TrackerCredentials.user_id==self.request.user.id).one()
            DBSession.delete(credentials)
            back_url = self.request.url_for('/tracker/list')
            return HTTPFound(location=back_url)
        return dict(
            type_name=u'tracker',
            title=self._(u'Credentials for user ${name} on tracker ${tracker}', name=self.request.user.name, tracker=tracker.name),
            url=self.request.url_for('/tracker/delete_login', tracker_id=tracker.id),
            back_url=self.request.url_for('/tracker/list'),
            form=form
        )
