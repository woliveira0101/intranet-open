# -*- coding: utf-8 -*-
import os
import base64
import mimetypes
import datetime
import calendar

from pyramid.view import view_config
from pyramid.exceptions import Forbidden
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.response import Response

from intranet3.utils.views import BaseView
from intranet3.models import User
from intranet3.forms.user import UserEditForm
from intranet3.log import INFO_LOG
from intranet3 import helpers as h
from intranet3.api.preview import Preview


LOG = INFO_LOG(__name__)


@view_config(route_name='user_list', permission='can_view_users')
class List(BaseView):
    def get(self):
        return {}

@view_config(route_name='user_view', permission='can_view_users')
class View(BaseView):
    def get(self):
        user_id = self.request.GET.get('user_id')
        user = User.query.get(user_id)
        return dict(user=user)


@view_config(route_name='user_edit', permission='can_edit_own_profile')
class Edit(BaseView):

    def dispatch(self):
        user_id = self.request.GET.get('user_id')

        if user_id and self.request.has_perm('can_edit_users'):
            user = User.query.get(user_id)
        elif user_id:
            raise Forbidden()
        else:
            user = self.request.user

        form = UserEditForm(self.request.POST, obj=user)
        if self.request.method == 'POST' and form.validate():
            user.availability_link = form.availability_link.data or None
            user.tasks_link = form.tasks_link.data or None
            user.skype = form.skype.data or None
            user.phone = form.phone.data or None
            user.phone_on_desk = form.phone_on_desk.data or None
            user.irc = form.irc.data or None
            user.location = form.location.data or None
            user.start_work = form.start_work.data or None
            user.description = form.description.data or None
            user.date_of_birth = form.date_of_birth.data or None
            user.roles = form.roles.data
            if self.request.has_perm('can_edit_users'):
                user.is_active = form.is_active.data
                user.start_full_time_work = form.start_full_time_work.data or None
                user.stop_work = form.stop_work.data or None
                user.employment_contract = form.employment_contract.data

            if self.request.has_perm('can_add_user_to_group'):
                groups = form.groups.data
                if "freelancer" in groups:
                    groups.remove('freelancer')
                    user.freelancer = True
                else:
                    user.freelancer = False

                if 'coordinator' in user.groups:
                    groups.append('coordinator')
                user.groups = groups

            if form.avatar.data:
                preview = Preview(self.request)
                if not preview.swap_avatar(type='users', id=user.id):
                    self.flash(self._(u"No preview to swap"))

            self.flash(self._(u"User data saved"))
            LOG(u"User data saved")
            if user_id and self.request.has_perm('can_edit_users'):
                return HTTPFound(location=self.request.url_for('/user/edit', user_id=user_id))
            else:
                return HTTPFound(location=self.request.url_for('/user/edit'))

        if user.freelancer:
            form.groups.data = user.groups + ['freelancer']
        return dict(id=user.id, user=user, form=form)


@view_config(route_name='user_tooltip', permission='can_view_users')
class Tooltip(BaseView):
    def get(self):
        user_id = self.request.GET.get('user_id')
        user = User.query.get(user_id)
        return dict(user=user)


def _avatar_path(user_id, settings, temp=False):
    user_id = str(user_id)
    if temp:
        return os.path.join(settings['AVATAR_PATH'], 'previews', user_id)
    return os.path.join(settings['AVATAR_PATH'], 'users', user_id)


@view_config(route_name='user_avatar', permission='can_view_users')
class Avatar(BaseView):
    def _file_read(self, path):
        if os.path.exists(path):
            try:
                f = open(path)
                data = f.read()
                f.close()
                return data
            except IOError as e:
                LOG(e)
        return None


    def _avatar(self, user_id, temp=False):
        return self._file_read(_avatar_path(user_id, self.request.registry.settings, temp))

    def _response(self, data):
        if data is None:
            raise HTTPNotFound()
        else:
            response = Response(data)
            response.headers['Content-Type'] = 'image/png'
            return response

    def get(self):
        user_id = self.request.GET.get('user_id')
        data = self._avatar(user_id)
        if data is None:
            path = os.path.normpath(os.path.join(os.path.dirname(__file__),'..','static','img','anonymous.png'))
            data = self._file_read(path)
        return self._response(data)

