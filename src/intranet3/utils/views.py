import datetime
import calendar
import json

from pyramid.httpexceptions import HTTPBadRequest, HTTPForbidden, HTTPNotFound

from intranet3 import models
from pyramid.i18n import TranslationStringFactory, get_localizer
from intranet3.log import INFO_LOG

LOG = INFO_LOG(__name__)


class View(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.flash = lambda message, klass='': request.session.flash((klass, message))
        self.session = request.db_session
        self.settings = self.request.registry.settings # shortcut

        tsf = TranslationStringFactory('intranet3')
        localizer = get_localizer(request)

        def _(string, **kwargs):
            return localizer.translate(tsf(string, mapping=kwargs))
        self._ = _

        # inside view cache, put here objects that will be used further in processing
        # for example after validation client object in protect() method the same object will be used in tmpl_ctx or main part of view (get method)
        self.v = {}


class BaseView(View):
    def _note_presence(self):
        """
        Check if request IP equals database-stored office IP.
        If it does, add a presence entry.
        If no office IP was configured, this method does nothing.
        Adds a presence entry to the datastore
        """
        office_ips = models.ApplicationConfig.get_office_ip()
        if not office_ips: # not yet configured
            return
        current_ip = self.request.remote_addr
        for office_ip in office_ips:
            if current_ip.startswith(office_ip):
                presence = models.PresenceEntry(url=self.request.url, user_id=self.request.user.id)
                self.session.add(presence)
                LOG(u'Noticed presence of user %s (%s)' % (self.request.user.email, current_ip))
                break
        else:
            LOG(u'User %s presence ignored (%s)' % (self.request.user.email, current_ip))

    def protect(self):
        """
        Override this method to check condtition and rise HTTPForbidden or not
        """

    def tmpl_ctx(self):
        return {}

    def dispatch(self):
        if self.request.method == 'GET':
            return self.get()
        elif self.request.method == 'POST':
            return self.post()
        else:
            raise HTTPNotFound()

    def __call__(self):
        self.protect()
        self._note_presence()
        self.request.tmpl_ctx.update(self.tmpl_ctx())
        return self.dispatch()

    def get(self):
        raise HTTPNotFound()

    def post(self):
        raise HTTPNotFound()


class ApiView(BaseView):

    def __init__(self, context, request):
        def response_exception(request, response):
            try:
                response.content_type = "application/json"
                response.body = json.dumps({'message': response.exception.message})
                return response
            except AttributeError:
                return response
        request.add_response_callback(response_exception)
        
        super(ApiView, self).__init__(context, request)


class CronView(View):
    def __call__(self):
        return self.action()

    def action(self):
        raise HTTPNotFound()


class MonthMixin(object):
    """
    Mixin for creating start and end date of month from GET month parameter('%m.%y')
    """
    def _get_month(self):
        try:
            month = self.request.GET.get('month')
            month, year = month.split('.')
            month, year = int(month), int(year)
            start_date = datetime.date(year, month, 1)
        except ValueError:
            raise HTTPBadRequest()
        else:
            day_of_week, days_in_month = calendar.monthrange(year, month)
            end_date = datetime.date(year, month, days_in_month)
            return start_date, end_date

