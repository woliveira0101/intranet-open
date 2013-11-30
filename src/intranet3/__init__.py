import sys
import os
import ConfigParser
import inspect

import pyramid_jinja2
from zope.interface import implementer
from sqlalchemy import engine_from_config
from pyramid.interfaces import IAuthenticationPolicy
from pyramid import paster
from pyramid.config import Configurator
from pyramid_beaker import session_factory_from_settings
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.security import Allow, Authenticated, ALL_PERMISSIONS
from werkzeug.contrib.cache import MemcachedCache

from twisted.web.wsgi import WSGIResource
from twisted.internet import reactor
from twisted.web import server


@implementer(IAuthenticationPolicy)
class CustomAuthenticationPolicy(AuthTktAuthenticationPolicy):
    def unauthenticated_userid(self, request):
        result = super(CustomAuthenticationPolicy, self).unauthenticated_userid(request)
        if result is None:
            cron_key = request.registry.settings['CRON_SECRET_KEY']
            if request.headers.get('X-Intranet-Cron', 'false') == cron_key:
                result = 0 # cron userid
        return result


class Root(object):

    PERMS = (
        ('',                          ('freelancer', 'employee', 'coordinator', 'scrum master', 'business', 'hr', 'client',)),
        ('users',                     ('A',          'A',        ' ',           ' ',            ' ',        ' ',  ' ',     )),
        ('bugs_owner',                ('A',          'A',        ' ',           ' ',            ' ',        ' ',  ' ',     )),
        ('wrongtime_justification',   ('A',          'A',        ' ',           ' ',            ' ',        ' ',  ' ',     )),
        ('late_justification',        (' ',          'A',        ' ',           ' ',            ' ',        ' ',  ' ',     )),
        ('view_presence',             (' ',          'A',        ' ',           ' ',            ' ',        ' ',  ' ',     )),
        ('edit_presence',             (' ',          'A',        ' ',           ' ',            ' ',        ' ',  ' ',     )),
        ('task_pivot',                (' ',          'A',        ' ',           ' ',            ' ',        ' ',  ' ',     )),
        ('view_teams',                (' ',          'A',        ' ',           ' ',            ' ',        ' ',  ' ',     )),
        ('view_sprints',              (' ',          'A',        ' ',           ' ',            ' ',        ' ',  ' ',     )),
        ('client_stuff',              (' ',          'A',        ' ',           ' ',            ' ',        ' ',  'A',     )),
        ('edit_sprints',              (' ',          ' ',        'A',           'A',            ' ',        ' ',  ' ',     )),
        ('view_clients',              (' ',          ' ',        'A',           'A',            ' ',        ' ',  ' ',     )),
        ('view_projects',             (' ',          ' ',        'A',           'A',            ' ',        ' ',  ' ',     )),
        ('edit_clients',              (' ',          ' ',        'A',           ' ',            ' ',        ' ',  ' ',     )),
        ('edit_projects',             (' ',          ' ',        'A',           ' ',            ' ',        ' ',  ' ',     )),
        ('edit_teams',                (' ',          ' ',        ' ',           ' ',            ' ',        'A',  ' ',     )),
        ('times_monthly_reports',     (' ',          ' ',        ' ',           ' ',            ' ',        'A',  ' ',     )),
        ('hr_stuff',                  (' ',          ' ',        ' ',           ' ',            ' ',        'A',  ' ',     )),
        ('see_inactive_users',        (' ',          ' ',        ' ',           ' ',            ' ',        'A',  ' ',     )),
        ('edit_user',                 (' ',          ' ',        ' ',           ' ',            ' ',        'A',  ' ',     )),
        ('times_reports',             (' ',          ' ',        ' ',           ' ',            'A',        ' ',  ' ',     )),

        # ADMIN ONLY:
        ('edit_config',               (' ',          ' ',        ' ',           ' ',            ' ',        ' ',  ' ',     )),
        ('edit_trackers',             (' ',          ' ',        ' ',           ' ',            ' ',        ' ',  ' ',     )),
        ('delete_projects',           (' ',          ' ',        ' ',           ' ',            ' ',        ' ',  ' ',     )),
        ('delete_clients',            (' ',          ' ',        ' ',           ' ',            ' ',        ' ',  ' ',     )),
        ('edit_users_timeentry',      (' ',          ' ',        ' ',           ' ',            ' ',        ' ',  ' ',     )),
        ('view_users_timeentry',      (' ',          ' ',        ' ',           ' ',            ' ',        ' ',  ' ',     )),
    )

    @staticmethod
    def generate(perms):
        base = [
            (Allow, Authenticated, ('view',)),
            (Allow, 'g:cron', 'cron'),
            (Allow, 'g:admin', ALL_PERMISSIONS),
        ]
        groups = perms[0][1]

        perms = perms[1:]

        result = {group: [] for group in groups}
        for perm, checklist in perms:
            for group, check in zip(groups, checklist):
                # perm, group, check
                if check == 'A':
                    result[group].append(perm)
                elif check != ' ':
                    raise Exception('%s not supported' % check)

        dynamic = []
        for group, perms in result.iteritems():
            dynamic.append((Allow, 'g:%s' % group, perms))

        return base + dynamic


    def __init__(self, request):
        self.request = request

Root.__acl__ = Root.generate(Root.PERMS)

config = None
memcache = None


def main(global_config, **settings):
    """
    Creates wsgi app
    """
    global config
    config = settings
    global memcache
    memcache = MemcachedCache([config['MEMCACHE_URI']])

    from intranet3.models import DBSession, Base, User
    from intranet3.utils import request
    from intranet3.views.auth import forbidden_view

    def groupfinder(userid, request):
        if userid == 0: ## cron userid
            perm = ['g:cron']
        else:
            user = User.query.get(userid)
            perm = [ 'g:%s' % g for g in user.groups ]
            if user.freelancer:
                perm.append('g:freelancer')
        return perm

    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    session_factory = session_factory_from_settings(settings)
    authn_policy = CustomAuthenticationPolicy(config['SESSION_KEY'], callback=groupfinder)
    authz_policy = ACLAuthorizationPolicy()
    pyramid_config = Configurator(
        settings=settings,
        authentication_policy=authn_policy,
        authorization_policy=authz_policy,
        session_factory=session_factory,
        request_factory=request.Request,
        default_permission='view',
        root_factory=Root,
    )
    pyramid_config.add_forbidden_view(forbidden_view)

    pyramid_config.add_static_view('static', 'static', cache_max_age=3600)

    #beta:
    #pyramid_config.add_route('api_my_bugs', '/api/bugs')
    #pyramid_config.add_route('api_time_collection', '/api/times')
    #pyramid_config.add_route('api_time', '/api/times/{id:\d+}')

    pyramid_config.add_route('api_team', '/api/teams/{team_id:\d+}')
    pyramid_config.add_route('api_teams', '/api/teams')
    pyramid_config.add_route('api_users', '/api/users')
    pyramid_config.add_route('api_preview', '/api/preview')
    pyramid_config.add_route('api_images', '/api/images/{type:\w+}/{id:\d+}')
    pyramid_config.add_route('api_presence', 'api/presence')
    pyramid_config.add_route('api_blacklist', 'api/blacklist')
    pyramid_config.add_route('api_lateness', '/api/lateness')
    pyramid_config.add_route('api_absence', '/api/absence')
    pyramid_config.add_route('api_absence_days', '/api/absence_days')

    pyramid_config.add_renderer('.html', 'pyramid_jinja2.renderer_factory')
    pyramid_config.add_renderer(None, 'intranet3.utils.renderer.renderer_factory')
    pyramid_config.add_translation_dirs('intranet3:locale/')

    jinja2_env = pyramid_config.get_jinja2_environment()
    from intranet3.utils import filters

    jinja2_env.filters['slugify'] = filters.slugify
    jinja2_env.filters['parse_datetime_to_miliseconds'] = filters.parse_datetime_to_miliseconds
    jinja2_env.filters['parse_user_email'] = filters.parse_user_email
    jinja2_env.filters['timedelta_to_minutes'] = filters.timedelta_to_minutes
    jinja2_env.filters['format_time'] = filters.format_time
    jinja2_env.filters['dictsort2'] = filters.do_dictsort
    jinja2_env.filters['tojson'] = filters.tojson
    jinja2_env.filters['comma_number'] = filters.comma_number
    jinja2_env.filters['first_words'] = filters.first_words
    jinja2_env.filters['first_words'] = filters.first_words

    jinja2_env.filters['is_true'] = filters.is_true
    jinja2_env.filters['is_false'] = filters.is_false
    jinja2_env.filters['initials'] = filters.initials
    jinja2_env.filters['int_or_float'] = filters.int_or_float
    jinja2_env.filters['markdown'] = filters.markdown_filter
    jinja2_env.globals.update(zip=zip)

    pyramid_config.include('pyramid_autoroute')
    if 'venusian.ignore' in settings:
        venusian_ingore = settings.get('venusian.ignore')
    else:
        venusian_ingore = None
    pyramid_config.scan(ignore=venusian_ingore)

    pyramid_config.add_settings({
        'TEMPLATE_DIR': os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates'),
    })


    app = pyramid_config.make_wsgi_app()
    return app


def run():
    argv = sys.argv[1:]
    if argv:
        config_file_path = argv[0]
    else:
        caller_file = inspect.getouterframes(inspect.currentframe())[1][1]
        caller_file = os.path.realpath(caller_file)
        buildout_dir = os.path.dirname(os.path.dirname(caller_file))
        config_file_path = os.path.join(buildout_dir, 'parts', 'etc', 'config.ini')

    if not os.path.isfile(config_file_path):
        print u'Path to config file must be given as a single parameter, for example "bin/run parts/etc/config.ini"'
        return

    paster.setup_logging(config_file_path)
    settings = paster.get_appsettings(config_file_path)

    app = main(None, **settings)

    from intranet3 import cron
    if not config.get('CRON_DISABLE'):
        cron.run_cron_tasks()

    for directory in ['users', 'teams', 'previews']:
        if not os.path.exists(os.path.join(settings['AVATAR_PATH'], directory)):
            os.makedirs(os.path.join(settings['AVATAR_PATH'], directory))

    full_config_path = os.path.abspath(config_file_path)
    server_config = ConfigParser.ConfigParser()
    server_config.readfp(open(full_config_path))
    port = server_config.getint('server:main', 'port')
    host = server_config.get('server:main', 'host')
    resource = WSGIResource(reactor, reactor.getThreadPool(), app)
    site = server.Site(resource)
    reactor.listenTCP(port, site)
    reactor.run()
