from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound

@view_config(route_name='root', permission='view')
def root(request):
    if request.wants_mobile:
        location = request.url_for('/mobile/user/list')
    elif 'client' in request.user.groups:
        location = request.url_for('/scrum/sprint/list')
    elif 'business' in request.user.groups:
        location = request.url_for('/times/tickets/report')
    elif 'hr' in request.user.groups:
        location = request.url_for('/presence/list')
    else:
        location = request.url_for('/bugs/my')
    return HTTPFound(location=location)
