# -*- coding: utf-8 -*-
import datetime

from pyramid.view import view_config
from pyramid.response import Response
from pyramid.renderers import render

from intranet3 import config
from intranet3.utils.views import CronView
from intranet3.models import User, Project
from intranet3.log import INFO_LOG, DEBUG_LOG, EXCEPTION_LOG
from intranet3.utils.mail import EmailSender
from intranet3.lib.bugs import Bugs

LOG = INFO_LOG(__name__)
DEBUG = DEBUG_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)

@view_config(route_name='cron_bugs_oldbugsreport', permission='cron')
class OldBugsReport(CronView):

    def _prepare_bugs(self, user, bugs):
        for bug in Bugs(self.request, user).get_user():
            if not hasattr(bug, 'project') or not hasattr(bug.project, 'coordinator_id'):
                continue
            coordinator_id = bug.project.coordinator_id
            if coordinator_id not in bugs:
                bugs[coordinator_id] = [[], []]

            bug_id = bug.tracker.id, bug.tracker.name, bug.id
            if bug_id not in bugs[coordinator_id][0]:
                bugs[coordinator_id][0].append(bug_id)
                bugs[coordinator_id][1].append(bug)

            if bug_id not in bugs['__all__'][0]:
                bugs['__all__'][0].append(bug_id)
                bugs['__all__'][1].append(bug)

        bugs = dict(
            (k, [v[0], sorted(v[1], key=lambda b: b.changeddate.replace(tzinfo=None))])
            for k, v in bugs.items()
        )

        return bugs

    def _send_report(self, coordinator, email, bugs):
        def on_success(result):
            LOG(u'Monthly report with old bugs - sent')
        def on_error(err):
            EXCEPTION(u'Failed to sent Monthly report with old bugs')

        if coordinator in bugs:
            data = {'bugs': bugs[coordinator][1][:20],
                    'title': self._(u'Lista najstarszych niezamkniętych bugów\nw projektach w których jesteś koordynatorem')}

            response = render(
                'intranet3:templates/_email_reports/old_bugs_report.html',
                data,
                request=self.request
            )
            deferred = EmailSender.send_html(
                email,
                self._(u'[Intranet2] Old bugs report'),
                response
            )
            deferred.addCallbacks(on_success, on_error)

    def action(self):
        coordinators = self.session.query(Project.coordinator_id, User.email, User.name, User)\
                                   .join(User)\
                                   .filter(Project.coordinator_id!=None)\
                                   .group_by(Project.coordinator_id, User)\
                                   .all()
        # prepare bugs
        bugs = {'__all__': [[], []]}
        for user_id, user_email, user_name, user in coordinators:
            bugs = self._prepare_bugs(user, bugs)

        # send report
        for user_id, user_email, user_name, user in coordinators:
            self._send_report(user_id, user_email, bugs)

        self._send_report('__all__', config['MANAGER_EMAIL'], bugs)

        return Response('ok')




