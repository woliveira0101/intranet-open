# -*- coding: utf-8 -*
import os
import mimetypes
import base64

from pyramid.httpexceptions import HTTPBadRequest, HTTPOk
from pyramid.view import view_config
from pyramid.response import Response

from intranet3.utils.views import ApiView
from intranet3 import helpers as h


class Preview(object):
    
    def __init__(self, request):
        self.request = request
        
    def avatar_path(self, img, settings, src):
        return os.path.join(settings['AVATAR_PATH'], src, str(img))
        
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
    
    def swap_avatar(self, destination, img):
        user_id = self.request.user.id
        path_temp = self.avatar_path(user_id, self.request.registry.settings, 'previews')
        path = self.avatar_path(img, self.request.registry.settings, destination)
        
        if os.path.exists(path):
            os.remove(path)
            
        try:
            os.rename(path_temp, path)
        except OSError:
            return -1
        
        return 0
        

class PreviewApi(ApiView):
    
    def _response(self, data):
        if data is None:
            raise HTTPNotFound()
        else:
            response = Response(data)
            response.headers['Content-Type'] = 'image/png'
            return response
            
    @view_config(route_name='api_upload_preview', request_method='GET')
    def get(self):
        filename = str(self.request.user.id)
        path_temp = os.path.join(self.settings['AVATAR_PATH'], 'previews', filename)
        return self._response(open(path_temp, 'rb').read())
    
    @view_config(route_name='api_upload_preview', request_method='POST', renderer='json')        
    def post(self):
        preview = Preview(self.request)
        
        type_pv = self.request.GET.get('type')
        if type_pv not in [u'team', u'user']:
            raise HTTPBadRequest('Expect type = team or user')
        
        if type_pv=='team':
            width = 77
            height = 77
        elif type_pv=='user':
            width = 100
            height = 100
            
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
                'url': self.request.route_url('api_upload_preview'),
                'filename': filename,
                'mime': mimetype,
                'size': size
            }
            
        return res
        
    @view_config(route_name='api_preview', request_method='GET', renderer='json')
    def swap_preview(self):
        destination = self.request.matchdict.get('destination')
        img = self.request.matchdict.get('img')
        preview = Preview(self.request)
        result = preview.swap_avatar(destination, img)
        if result == 0:
            return HTTPOk("OK")
        else:
            raise HTTPBadRequest('No such file or directory')

