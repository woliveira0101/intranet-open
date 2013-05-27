# -*- test-case-name: twisted.test.test_twistd -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
The Twisted Daemon: platform-independent interface.

@author: Christopher Armstrong
"""

from twisted.application import app

from _twistd_unix import ServerOptions, \
    UnixApplicationRunner as _SomeApplicationRunner


def runApp(config):
    _SomeApplicationRunner(config).run()


def run():
    app.run(runApp, ServerOptions)


__all__ = ['run', 'runApp']
