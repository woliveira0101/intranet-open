from pyramid.httpexceptions import HTTPForbidden

class HasPerm(object):
    def __init__(self, perm):
        self.perm = perm

    def __call__(self, func):
        self.func = func

        def wrap(handler_instance, *args, **kw):
            if not handler_instance.request.has_perm(self.perm):
                raise HTTPForbidden()
            return self.func(handler_instance, *args, **kw)

        return wrap

has_perm = HasPerm
