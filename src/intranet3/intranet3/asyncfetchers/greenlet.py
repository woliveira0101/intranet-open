import gevent

class Greenlet(gevent.Greenlet):
    """
    Greenlet class with some custom modifications
    """

    def __init__(self, *args, **kwargs):
        super(Greenlet, self).__init__(*args, **kwargs)
        self._traceback = None
        # HACK: supress printing traceback to stderr:
        self.parent.print_exception = lambda *args, **kwargs: None

    def _report_error(self, exc_info):
        """
        HACK:
        To reraise exception with proper traceback we have to save it in
        self._traceback and then use it in reraise_exc
        """
        super(Greenlet, self)._report_error(exc_info)
        self._traceback = exc_info[2]


    def reraise_exc(self):
        """
        Shortcut for rerasing exceptions in greelet
        """
        if not self.successful():
            raise self.exception, None, self.traceback


    @property
    def traceback(self):
        return self._traceback

