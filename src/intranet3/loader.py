import os
import ConfigParser

from pyramid import paster
from twisted.python import log
from twisted.internet import reactor


class HttpsSchemeFixer(object):
    """ Rewrites wsgi.url_scheme environment variable to 'https' """

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        scheme = environ.get('HTTP_X_URL_SCHEME')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)

def get_application(*args):
    config_file_path = os.environ.get('INTRANET2_CONFIG', '')
    assert config_file_path, u'Config file path must be given in INTRANET2_CONFIG environment variable'

    observer = log.PythonLoggingObserver()
    observer.start()

    config = ConfigParser.ConfigParser()
    config.read(config_file_path)

    from intranet3 import main
    paster.setup_logging(config_file_path)
    settings = paster.get_appsettings(config_file_path)

    app = main(None, **settings)

    from intranet3 import cron
    if not settings.get('CRON_DISABLE'):
        cron.run_cron_tasks()

    if config.getboolean('server:main', 'proxy_fix'):
        from werkzeug.contrib.fixers import ProxyFix
        app = ProxyFix(app)

    if config.getboolean('server:main', 'scheme_fix'):
        app = HttpsSchemeFixer(app)

    return app

reactor.suggestThreadPoolSize(50)
application = get_application()
