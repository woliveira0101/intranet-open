from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPForbidden

from intranet3.utils.views import BaseView

from intranet3.forms import config as config_forms
from intranet3.models import ApplicationConfig
from intranet3.log import INFO_LOG

LOG = INFO_LOG(__name__)

@view_config(route_name='config_view', permission='can_edit_config')
class View(BaseView):
    def dispatch(self):
        subpage = self.request.GET.get('subpage', 'general')
        if subpage not in ['general', 'reports', 'spreadsheets', 'access']:
            return HTTPForbidden()

        config_obj = ApplicationConfig.get_current_config(allow_empty=True)

        FormRef = getattr(config_forms, "%sForm"% subpage.title())

        if config_obj is not None:
            LOG(u"Found config object from %s" % (config_obj.date, ))
            form = FormRef(self.request.POST, obj=config_obj) 
        else:
            LOG(u"Config object not found")
            form = FormRef(self.request.POST)

        if self.request.method == 'POST' and form.validate():
            if config_obj is None:
                config_obj =  ApplicationConfig()

            # Add/Edit data
            if subpage == 'general':
                config_obj.office_ip = form.office_ip.data
                config_obj.google_user_email = form.google_user_email.data
                config_obj.google_user_password = form.google_user_password.data
                config_obj.cleaning_time_presence = form.cleaning_time_presence.data
                config_obj.absence_project_id = form.absence_project_id.data if form.absence_project_id.data else None
                config_obj.monthly_late_limit = form.monthly_late_limit.data
                config_obj.monthly_incorrect_time_record_limit = form.monthly_incorrect_time_record_limit.data
            elif subpage == 'reports':
                config_obj.reports_project_ids = [int(id) for id in form.reports_project_ids.data]
                config_obj.reports_omit_user_ids = [int(id) for id in form.reports_omit_user_ids.data]
                config_obj.reports_without_ticket_project_ids = [int(id) for id in form.reports_without_ticket_project_ids.data]
                config_obj.reports_without_ticket_omit_user_ids = [int(id) for id in form.reports_without_ticket_omit_user_ids.data]
            elif subpage == 'spreadsheets':
                config_obj.holidays_spreadsheet = form.holidays_spreadsheet.data
                config_obj.hours_employee_project = form.hours_employee_project.data
                config_obj.hours_ticket_user_id = form.hours_ticket_user_id.data if form.hours_ticket_user_id.data else None
            elif subpage == "access":
                config_obj.freelancers = form.freelancers.data
  
            self.session.add(config_obj)
            config_obj.invalidate_office_ip()
  
            LOG(u"Config object saved")
            self.flash(self._(u'Application Config saved'), klass='success')
            return HTTPFound(location=self.request.url_for('/config/view', subpage=subpage))

        return dict(
            form=form,
            subpage=subpage
        )
