import requests
from oauth2client.client import FlowExchangeError
from pyramid.view import view_config
from pyramid.security import authenticated_userid, remember, forget, NO_PERMISSION_REQUIRED
from pyramid.httpexceptions import HTTPForbidden, HTTPFound

from intranet3 import config
from intranet3.ext.oauth2 import OAuth2WebServerFlow
from intranet3.models import ApplicationConfig, User, Client
from intranet3.log import DEBUG_LOG, INFO_LOG, WARN_LOG

DEBUG = DEBUG_LOG(__name__)
LOG = INFO_LOG(__name__)
WARN = WARN_LOG(__name__)
USER_INFO_URI = 'https://www.googleapis.com/oauth2/v1/userinfo?access_token=%s'

users_flow = OAuth2WebServerFlow(
    client_id=config['GOOGLE_CLIENT_ID'],
    client_secret=config['GOOGLE_CLIENT_SECRET'],
    scope=[
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/calendar.readonly',
        ],
    redirect_uri=config['FRONTEND_PREFIX'] + '/auth/callback',
)

clients_flow = OAuth2WebServerFlow(
    client_id=config['GOOGLE_CLIENT_ID'],
    client_secret=config['GOOGLE_CLIENT_SECRET'],
    scope=[
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
        ],
    redirect_uri=config['FRONTEND_PREFIX'] + '/auth/callback',
)
flow = users_flow
freelancers_flow = clients_flow


def forbidden_view(request):
    if authenticated_userid(request):
        return HTTPForbidden()
    else:
        return HTTPFound(location=request.url_for('/auth/logout_view'))


@view_config(route_name='auth_callback', permission=NO_PERMISSION_REQUIRED)
def callback(request):
    code = request.params.get('code', '')
    try:
        credentials = flow.step2_exchange(code)
    except FlowExchangeError:
        raise HTTPForbidden
    data = requests.get(USER_INFO_URI % credentials.access_token, verify=False)
    google_profile = data.json

    email = google_profile['email']
    email = 'marcin.orlowski@stxnext.pl'

    EXTRA_EMAILS = request.registry.settings.get('GOOGLE_EXTRA_EMAILS', '').split('\n')
    config = ApplicationConfig.get_current_config(allow_empty=True)
    freelancers = config.get_freelancers()
    clients_emails = Client.get_emails()
    if email.endswith('@%s' % request.registry.settings['COMPANY_DOMAIN']) or email in EXTRA_EMAILS:
        group = 'employee'
    elif email in freelancers:
        group = 'freelancer'
    elif email in clients_emails:
        group = 'client'
    else:
        WARN_LOG(u"Forbidden acccess for profile:\n%s\n client's emails:\n%s\nfreelancer's emails:\n%s" % (google_profile, clients_emails, freelancers))
        return HTTPForbidden()

    session = request.db_session
    user = session.query(User).filter(User.email==email).first()
    if user is not None:
        if credentials.refresh_token:
            DEBUG(u'Adding refresh token %s for user %s' % (
                credentials.refresh_token, user.name,
            ))
            user.refresh_token = credentials.refresh_token
            session.add(user)
        DEBUG(u'Signing in existing user %s' % (user.name, ))
    else:
        LOG(u'Creating new user with name %s and email %s, group: %s' % (google_profile['name'], google_profile['email'], group))
        user = User(
            name=google_profile['name'],
            email=email,
            refresh_token=credentials.refresh_token or '',
            groups=[group],
        )

        session.add(user)
        session.flush()
    headers = remember(request, user.id)
    DEBUG(u'User %s set' % user.name)
    if group == 'client':
        location = request.url_for('/scrum/sprint/list')
    else:
        location = '/'
    return HTTPFound(
        location=location,
        headers=headers,
    )

@view_config(route_name='logout', permission=NO_PERMISSION_REQUIRED)
def logout(request):
    headers = forget(request)
    return HTTPFound(
        location=request.url_for('/auth/logout_view'),
        headers=headers
    )

@view_config(route_name='logout_view', permission=NO_PERMISSION_REQUIRED)
def logout_view(request):
    users_link = users_flow.step1_get_authorize_url()
    clients_link = clients_flow.step1_get_authorize_url()
    freelancers_link = freelancers_flow.step1_get_authorize_url()
    return dict(
        users_link=users_link,
        clients_link=clients_link,
        freelancers_link=freelancers_link,
    )

