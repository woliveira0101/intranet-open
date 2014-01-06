from pyramid.threadlocal import get_current_request

def flash(message, klass=''):
    """
    BIG HACK
    Use only if you are sure it will be called in request context
    If you can use flash function in BaseView class
    """
    request = get_current_request()
    if request:
        request.session.flash((klass, message))
