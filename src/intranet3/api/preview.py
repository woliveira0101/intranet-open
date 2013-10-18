# -*- coding: utf-8 -*
import os
import datetime
import mimetypes
import base64
import urllib
import string

from random import choice
from hashlib import md5

from pyramid.httpexceptions import HTTPBadRequest, HTTPNotFound
from pyramid.view import view_config
from pyramid.response import Response

from intranet3.utils.views import ApiView
from intranet3 import helpers as h
from intranet3.log import INFO_LOG
LOG = INFO_LOG(__name__)


class Preview(object):

    DESTINATIONS = {
        'users' : 'users',
        'teams': 'teams',
    }

    def __init__(self, request):
        self.request = request


    def avatar_path(self, directory, id):
        return os.path.join(self.request.registry.settings['AVATAR_PATH'], directory, str(id))

    def file_write(self, path, data):
        try:
            dir = os.path.dirname(path)
            if not os.path.exists(dir):
                os.makedirs(dir)
            f = open(path,'w')
            f.write(data)
            f.close()
        except OSError, e:
            LOG(e)

    def upload_data(self, data):
        if data[:5] == 'data:':
            info,data = data.split(';')
            if data[:6] == 'base64':
                data = base64.b64decode(data[7:])
            else:
                return ''
        return data

    def swap_avatar(self, type, id):
        directory = self.DESTINATIONS[type]
        user_id = self.request.user.id
        preview_path = self.avatar_path('previews', user_id)
        destination_path = self.avatar_path(directory, id)

        if os.path.exists(destination_path):
            os.remove(destination_path)

        try:
            os.rename(preview_path, destination_path)
        except OSError as e:
            return False

        return True


@view_config(route_name='api_preview', renderer='json')
class PreviewApi(ApiView):

    DIMENTIONS = {
        'team': (77, 77),
        'user': (100, 100),
    }

    def _response(self, data):
        if data is None:
            raise HTTPNotFound()
        else:
            response = Response(data)
            response.headers['Content-Type'] = 'image/png'
            return response

    def gravatar(self):
        random_str = 'teams'.join(choice(string.letters + string.digits) for i in xrange(10))
        hash = md5(random_str).hexdigest()
        params = urllib.urlencode({'s': '128', 'd': 'retro'}, doseq=True)
        uri = 'http://www.gravatar.com/avatar/%s?%s'% (hash, params)

        return urllib.urlopen(uri ).read()

    def get(self):
        filename = str(self.request.user.id)
        path_temp = os.path.join(self.settings['AVATAR_PATH'], 'previews', filename)

        # if there is no team's avatar, create gravatar:
        data = None
        is_file = os.path.isfile(path_temp)
        if is_file:
            modified = datetime.datetime.fromtimestamp(os.path.getmtime(path_temp))
            modifed = (datetime.datetime.now() - modified).seconds

            if modifed < 10:
                data = open(path_temp, 'rb').read()

        if not data:
            data = self.gravatar()
            Preview(self.request).file_write(path_temp, data)

        return self._response(data)


    def post(self):
        preview = Preview(self.request)

        type_pv = self.request.GET.get('type')
        if type_pv not in [u'team', u'user']:
            raise HTTPBadRequest('Expect type = team or user')

        width, height = self.DIMENTIONS[type_pv]

        res = dict(status='error', msg='', file={})
        file = self.request.POST['file']
        data = preview.upload_data(file.file.read())
        size = len(data)
        mimetype = mimetypes.guess_type(file.filename)[0]
        filename = str(self.request.user.id)
        if size and mimetype[:5] == 'image':
            data = h.image_resize(data, 's', width, height)
            preview.file_write(os.path.join(self.settings['AVATAR_PATH'], 'previews', filename), data)
            res['status'] = 'ok'
            res['file'] = {
                'url': '/api/images/previews/%s' % filename,
                'filename': filename,
                'mime': mimetype,
                'size': size
            }

        return res


@view_config(route_name='api_images', renderer='json', http_cache=60, permission='users')
class ImageApi(ApiView):
    ANONYMONUS = {
        'users': os.path.normpath(os.path.join(os.path.dirname(__file__),'..','static','img','anonymous.png')),
        'previews': os.path.normpath(os.path.join(os.path.dirname(__file__),'..','static','img','anonymous.png')),
        'teams': os.path.normpath(os.path.join(os.path.dirname(__file__),'..','static','img','anonymous_team.png')),
    }

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

    def _response(self, data):
        response = Response(data)
        response.headers['Content-Type'] = 'image/png'
        return response

    def get(self):
        type_ = self.request.matchdict.get('type')
        id_ = self.request.matchdict.get('id')
        if type_ not in ('previews', 'teams', 'users'):
            raise HTTPNotFound()


        path = os.path.join(self.settings['AVATAR_PATH'], type_, id_)
        data = self._file_read(path)
        if data is None:
            path = self.ANONYMONUS[type_]
            data = self._file_read(path)
        return self._response(data)