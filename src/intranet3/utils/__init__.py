from pyramid.events import subscriber
from pyramid.events import ContextFound

_flash = None

def flash(message, klass=''):
    """
    BIG HACK
    Use only if you are sure it will be called in request context
    If you can use flash function in BaseView class
    """
    if _flash:
        _flash((klass, message))

@subscriber(ContextFound)
def _get_flash(event):
    request = event.request
    global _flash
    _flash = event.request.session.flash
