from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound

@view_config(route_name='root', permission='client_or_freelancer')
def root(request):
    if 'client' in request.user.groups:
        location = request.url_for('/scrum/sprint/list')
    else:
        location = request.url_for('/bugs/my')
    return HTTPFound(location=location)
