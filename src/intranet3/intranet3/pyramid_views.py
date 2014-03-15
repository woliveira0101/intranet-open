from pyramid.response import Response
from pyramid.view import view_config, forbidden_view_config
from pyramid.security import authenticated_userid, NO_PERMISSION_REQUIRED
from pyramid.httpexceptions import HTTPForbidden, HTTPFound


@forbidden_view_config()
def forbidden_view(request):
    if authenticated_userid(request):
        return HTTPForbidden()
    else:
        return HTTPFound(location=request.url_for('/auth/logout_view'))


@view_config(context=Exception, permission=NO_PERMISSION_REQUIRED)
def failed_validation(exc, request):
    response =  Response('Ups, something went wrong :/')
    response.status_int = 500
    return response
