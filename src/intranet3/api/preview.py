# -*- coding: utf-8 -*
import os
import mimetypes
import base64

from pyramid.httpexceptions import HTTPBadRequest, HTTPNotFound
from pyramid.view import view_config, view_defaults
from pyramid.response import Response

from intranet3.utils.views import ApiView
from intranet3 import helpers as h


class Preview(object):
    
    DESTINATIONS = {
        'users' : 'user',
        'teams': 'team',
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
            import ipdb; ipdb.set_trace()
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
    
    def get(self):
        filename = str(self.request.user.id)
        path_temp = os.path.join(self.settings['AVATAR_PATH'], 'previews', filename)
        return self._response(open(path_temp, 'rb').read())
    
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
                'url': '/thumbs/previews/%s' % filename,
                'filename': filename,
                'mime': mimetype,
                'size': size
            }
            
        return res
