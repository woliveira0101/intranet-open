import re
import sys
import inspect

from zope.interface import implementer
from pyramid.interfaces import ITemplateRenderer
from pyramid_jinja2 import Jinja2TemplateRenderer, _get_or_build_default_environment

first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')

def convert(name):
    """
    From CamelCase to snake_case
    https://gist.github.com/3660565/f2e285d2e249b0ff042f524f0b74360e5d3535aa
    """
    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()

@implementer(ITemplateRenderer)
class Jinja2AutoTemplateRenderer(Jinja2TemplateRenderer):

    VIEWS_ROOT_MODULE = 'intranet3.views'
    TEMPLATES_DIR = 'intranet3:templates'

    def _get_callable_name(self, callable):
        if inspect.isfunction(callable):
            return callable.__module__, callable.func_name.lower()
        elif inspect.isclass(callable):
            name = convert(callable.__name__)
            return callable.__module__, name
        elif hasattr(callable, '__class__'):
            name = convert(callable.__class__.__name__)
            return callable.__module__, name

    def __call__(self, value, system):
        if not self.info.name:
            view = system['view']
            module, name = self._get_callable_name(view)
            pos = module.find(self.VIEWS_ROOT_MODULE)
            alen = len(self.VIEWS_ROOT_MODULE)
            rest = module[pos+alen:].replace('.', '/')
            path = '%s/%s' % (rest, name)
            path = '%s%s.html' % (self.TEMPLATES_DIR, path)
            try:
                system.update(value)
            except (TypeError, ValueError):
                ex = sys.exc_info()[1] # py2.5 - 3.2 compat
                raise ValueError('renderer was passed non-dictionary '
                                 'as value: %s' % str(ex))
            return self.environment.get_template(path).render(system)

        return super(Jinja2AutoTemplateRenderer, self).__call__(value, system)


def renderer_factory(info):
    environment = _get_or_build_default_environment(info.registry)
    return Jinja2AutoTemplateRenderer(info, environment)

