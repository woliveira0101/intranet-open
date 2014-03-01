import gevent.monkey
gevent.monkey.patch_all()
import psycogreen.gevent
psycogreen.gevent.patch_psycopg()

import os

from zope.interface import implementer
from sqlalchemy import engine_from_config
from pyramid.interfaces import IAuthenticationPolicy
from pyramid.config import Configurator
from pyramid_beaker import session_factory_from_settings
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from werkzeug.contrib.cache import MemcachedCache

try:
    import uwsgi
except:
    uwsgi = None


@implementer(IAuthenticationPolicy)
class CustomAuthenticationPolicy(AuthTktAuthenticationPolicy):
    def unauthenticated_userid(self, request):
        result = super(CustomAuthenticationPolicy, self).unauthenticated_userid(request)
        if result is None:
            cron_key = request.registry.settings['CRON_SECRET_KEY']
            if request.headers.get('X-Intranet-Cron', 'false') == cron_key:
                result = -1 # cron userid
        return result


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
    from intranet3.utils import request, acl

    def groupfinder(userid, request):
        if userid == -1: ## cron userid
            perm = ['g:cron']
        elif userid == -2: ## task userid
            perm = ['g:task']
        else:
            user = User.query.get(userid)
            perm = ['g:%s' % g for g in user.groups]
        return perm

    engine = engine_from_config(settings)
    engine.pool._use_threadlocal = True
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
        root_factory=acl.Root,
    )

    pyramid_config.add_static_view('static', 'static', cache_max_age=3600)

    #beta:
    #pyramid_config.add_route('api_my_bugs', '/api/bugs')
    #pyramid_config.add_route('api_time_collection', '/api/times')
    #pyramid_config.add_route('api_time', '/api/times/{id:\d+}')

    pyramid_config.add_route('api_team', '/api/teams/{team_id:\d+}')
    pyramid_config.add_route('api_teams', '/api/teams')

    pyramid_config.add_route('api_board', '/api/boards/{board_id:\d+}')
    pyramid_config.add_route('api_boards', '/api/boards')
    pyramid_config.add_route('api_sprint_bugs', '/api/sprint/{sprint_id:\d+}/bugs')

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

    is_production = (
        'DEBUG' not in settings or
        settings.get('DEBUG', '').lower() == 'false'
    )

    if uwsgi and is_production:
        from intranet3.cron import run_cron_tasks
        run_cron_tasks()

    app = pyramid_config.make_wsgi_app()
    return app
