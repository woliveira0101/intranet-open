# -*- coding: utf-8 -*-
import os
import base64
import mimetypes

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.response import Response

from intranet3.utils.views import BaseView
from intranet3.models import User
from intranet3.forms.user import UserEditForm
from intranet3.log import INFO_LOG
from intranet3 import helpers as h

LOG = INFO_LOG(__name__)


@view_config(route_name='user_list', permission='freelancer')
class List(BaseView):
    def get(self):
        users = User.query.filter(User.is_active==True)\
                          .filter(User.is_not_client())\
                          .filter(User.freelancer==False)\
                          .order_by(User.name).all()
        freelancers = User.query.filter(User.is_active==True)\
                                .filter(User.is_not_client())\
                                .filter(User.freelancer==True)\
                                .order_by(User.name).all()

        clients = []
        if self.request.has_perm('admin'):
            clients = User.query.filter(User.is_active==True)\
                                .filter(User.is_client())\
                                .order_by(User.name).all()


        return dict(
            users=users,
            freelancers=freelancers,
            clients=clients,
        )


@view_config(route_name='user_view')
class View(BaseView):
    def get(self):
        user_id = self.request.GET.get('user_id')
        user = User.query.get(user_id)
        return dict(user=user)


@view_config(route_name='user_edit', permission='freelancer')
class Edit(BaseView):
    def _change_avatar(self, user_id):
        path_temp = _avatar_path(user_id, self.request.registry.settings, True)
        path = _avatar_path(user_id, self.request.registry.settings)
        if os.path.exists(path):
            os.remove(path)
        os.rename(path_temp, path)

    def dispatch(self):
        user_id = self.request.GET.get('user_id')

        if user_id and self.request.has_perm('admin'):
            user = User.query.get(user_id)
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
            user.location = form.location.data
            user.start_work = form.start_work.data or None
            user.description = form.description.data or None
            if form.level.data:
                user.levels = reduce(lambda x,y:x|y,[int(x) for x in form.level.data])
            if self.request.has_perm('admin'):
                user.is_active = form.is_active.data
                user.groups = form.groups.data
                user.start_full_time_work = form.start_full_time_work.data or None
            user.is_programmer = form.is_programmer.data
            user.is_frontend_developer = form.is_frontend_developer.data
            user.is_graphic_designer = form.is_graphic_designer.data

            if form.avatar.data:
                self._change_avatar(user.id)

            self.flash(self._(u"User data saved"))
            LOG(u"User data saved")
            if user_id and self.request.has_perm('admin'):
                return HTTPFound(location=self.request.url_for('/user/edit', user_id=user_id))
            else:
                return HTTPFound(location=self.request.url_for('/user/edit'))
        return dict(id=user.id, user=user, form=form)


@view_config(route_name='user_tooltip', permission='freelancer')
class Tooltip(BaseView):
    def get(self):
        user_id = self.request.GET.get('user_id')
        user = User.query.get(user_id)
        return dict(user=user)


def _avatar_path(user_id, settings, temp=False):
    user_id = 'u' + str(user_id)
    if temp:
        user_id = 'temp_' + user_id
    return os.path.join(settings['AVATAR_PATH'], user_id)


@view_config(route_name='user_avatar', permission='freelancer')
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


@view_config(route_name='files_upload_avatar', renderer='json', permission='freelancer')
class UploadAvatar(BaseView):

    def _file_write(self, path, data):
        try:
            dir = os.path.dirname(path)
            if not os.path.exists(dir):
                os.makedirs(dir)
            f = open(path,'w')
            f.write(data)
            f.close()
        except OSError, e:
            LOG(e)

    def _upload_data(self, data):
        if data[:5] == 'data:':
            info,data = data.split(';')
            if data[:6] == 'base64':
                data = base64.b64decode(data[7:])
            else:
                return ''
        return data

    def dispatch(self):
        user_id = self.request.GET.get('user_id')
        if user_id and self.request.has_perm('admin'):
            user = User.query.get(user_id)
        else:
            user = self.request.user
        res = dict(status='error', msg='', file={})
        if self.request.method == 'POST':
            file = self.request.POST['file']
            data = self._upload_data(file.file.read())
            size = len(data)
            mimetype = mimetypes.guess_type(file.filename)[0]
            if size and mimetype[:5] == 'image':
                data = h.image_resize(data, 's', 100, 100)
                self._file_write(_avatar_path(user.id, self.request.registry.settings, True), data)
                res['status'] = 'ok'
                res['file'] = {
                    'url': self.request.url_for('/user/avatar_temp', user_id=user.id),
                    'filename':file.filename,
                    'mime':mimetype,
                    'size':size
                }
        return res

@view_config(route_name='files_avatar_temp', renderer='json', permission='freelancer')
class AvatarTemp(BaseView):
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
        path_temp = _avatar_path(user_id, self.request.registry.settings, True)
        return self._response(open(path_temp, 'rb').read())
