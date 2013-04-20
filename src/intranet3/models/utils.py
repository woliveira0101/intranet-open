

class ObjectTemporaryWrapper(object):
    """ Wrapper for models """

    def __init__(self, instance, **kwargs):
        """
        @param instance: model instance to wrap
        """
        super(ObjectTemporaryWrapper, self).__init__()
        object.__setattr__(self, '_instance', instance)
        for key, value in kwargs.iteritems():
            object.__setattr__(self, key, value)

    def __getattr__(self, name):
        return getattr(self._instance, name)


