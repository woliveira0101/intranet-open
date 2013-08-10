from twisted.application import app

from twisted.scripts._twistd_unix import UnixApplicationRunner, ServerOptions, UnixAppLogger
from twisted.web.server import Site

from monkey_patches import _openLogFile, _getLogObserver

def _monkey_patch_twistd_loggers():
    UnixAppLogger._getLogObserver = _getLogObserver
    Site._openLogFile = _openLogFile

def runApp(config):
    UnixApplicationRunner(config).run()


def run():
    _monkey_patch_twistd_loggers()
    app.run(runApp, ServerOptions)


__all__ = ['run', 'runApp']
