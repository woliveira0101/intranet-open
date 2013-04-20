from logging import getLogger

logger = getLogger('intranet3')
LOG = lambda msg: logger.info(msg)

def logger_producer(method, exc_info=False):
    def producer(name):
        logger = getLogger(name)
        func = getattr(logger, method)
        return (lambda msg: func(msg, exc_info=True)) if exc_info else (lambda msg: func(msg))
    return producer

INFO_LOG = logger_producer('info')
DEBUG_LOG = logger_producer('debug')
WARN_LOG = logger_producer('warning')
ERROR_LOG = logger_producer('error')
FATAL_LOG = logger_producer('fatal')
EXCEPTION_LOG = logger_producer('error', True)
