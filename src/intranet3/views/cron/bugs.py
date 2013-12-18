# -*- coding: utf-8 -*-
from pyramid.view import view_config
from pyramid.response import Response
from pyramid.renderers import render

from intranet3 import config
from intranet3.lib.bugs import Bugs
from intranet3.log import INFO_LOG, DEBUG_LOG, EXCEPTION_LOG
from intranet3.models import User, Project
from intranet3.utils.smtp import EmailSender
from intranet3.utils.views import CronView


LOG = INFO_LOG(__name__)
DEBUG = DEBUG_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)


@view_config(route_name='cron_bugs_oldbugsreport', permission='cron')
class OldBugsReport(CronView):

    def _send_report(self, coordinator_id, email, bugs):
        def on_success(result):
            LOG(u'Monthly report with old bugs - sent')
        def on_error(err):
            EXCEPTION(u'Failed to sent Monthly report with old bugs')

        # Bugs filtering & ordering
        # Coordinator gets bugs from his projects, manager gets bugs from
        # all projects
        if coordinator_id is None: # Manager
            bugs_filtered = sorted(
                bugs,
                key=lambda b: b.changeddate.replace(tzinfo=None),
            )
            title = u'Lista najstarszych niezamkniętych bugów\nwe wszystkich projektach'
        else: # Coordinator
            bugs_filtered = sorted(
                [b for b in bugs if b.project.coordinator_id == coordinator_id],
                key=lambda b: b.changeddate.replace(tzinfo=None),
            )
            title = u'Lista najstarszych niezamkniętych bugów\nw projektach w których jesteś koordynatorem'
        if bugs_filtered:
            data = {
                'bugs': bugs_filtered[:20],
                'title': self._(title),
            }
            response = render(
                'intranet3:templates/_email_reports/old_bugs_report.html',
                data,
                request=self.request
            )
            deferred = EmailSender.send_html(
                email,
                self._(u'[Intranet3] Old bugs report'),
                response
            )
            deferred.addCallbacks(on_success, on_error)

    def action(self):
        coordinators = self.session.query(Project.coordinator_id, User.email) \
                                   .join(User) \
                                   .filter(Project.coordinator_id!=None) \
                                   .group_by(Project.coordinator_id, User) \
                                   .all()
        manager = self.session.query(User) \
                              .filter(User.email == config['MANAGER_EMAIL']) \
                              .first()
        bugs = Bugs(self.request, manager).get_all()

        # Coordinators
        for user_id, user_email in coordinators:
            self._send_report(user_id, user_email, bugs)
        # Manager
        self._send_report(None, config['MANAGER_EMAIL'], bugs)

        return Response('ok')
