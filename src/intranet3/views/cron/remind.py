# -*- coding: utf-8 -*-
import datetime

from pyramid.view import view_config
from pyramid.response import Response

from intranet3.utils.views import CronView
from intranet3.models import User, Holiday
from intranet3.log import INFO_LOG, DEBUG_LOG, EXCEPTION_LOG
from intranet3.utils import mail
from intranet3.lib.bugs import Bugs

LOG = INFO_LOG(__name__)
DEBUG = DEBUG_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)


MIN_HOURS = 6.995 #record hours

@view_config(route_name='cron_bugs_missinghours', permission='cron')
class MissingHours(CronView):
    """ remind (via email) everyone about their missing hours """

    def HOURS_EMAIL_TEMPLATE(self, name='', actual='', min_hours='', date='', url=''):
        return self._(u"""Hej ${name}! Masz mniej (${actual}) niż ${min_hours} godzin wpisanych w intranecie za dzień ${date}.
Zapraszam do dodania brakujących wpisów pod adresem ${url}

Pozdrawiam
Twój intranet
    """, **locals())

    def _remind_missing_hours(self, email, name, hours, date):
        """ remind (via email) everyone about their missing hours """
        LOG(u"Starting email reminder for user %s" % (email, ))
        time_list_url = self.request.url_for('/times/list', date=date.strftime('%d.%m.%Y'))
        hours_url = self.settings['FRONTEND_PREFIX'] + time_list_url
        message = self.HOURS_EMAIL_TEMPLATE(
            name=name,
            min_hours=MIN_HOURS,
            actual='%.2f' % hours,
            url=hours_url,
            date=date.strftime('%d.%m.%Y'),
        )
        topic = self._(u"[intranet] brakujące godziny z dnia ${date}", date=date.strftime('%d.%m.%Y'))
        with mail.EmailSender() as email_sender:
            email_sender.send(
                email,
                topic,
                message,
            )
        LOG(u"Email reminder for user %s started" % (email, ))
        return message

    def action(self):
        if Holiday.is_holiday(datetime.date.today()):
            LOG(u"Skipping missing hours reminder, because it's a holiday")
            return Response(self._(u"Won't remind"))
        LOG(u"Starting missing hours reminder")

        today = datetime.date.today()
        entries = self.session.query('email', 'name', 'time').from_statement("""
        SELECT s.email, s.name, s.time FROM (
            SELECT u.email as "email", u.name as "name", (
                SELECT COALESCE(SUM(t.time), 0)
                FROM time_entry t
                WHERE t.user_id = u.id
                  AND t.date = :today
                  AND t.deleted = FALSE
            ) as "time"
            FROM "user" u
            WHERE NOT u.groups @> '{client}' AND u.is_active

        ) as s WHERE s.time < :min_hours
        """).params(today=today, min_hours=MIN_HOURS)

        for email, name, hours in entries:
            self._remind_missing_hours(email, name, hours, today)

        LOG(u"Ending resolved bugs reminder")
        return Response(self._(u'Reminded everybody'))


@view_config(route_name='cron_remind_resolvedbugs', permission='cron')
class ResolvedBugs(CronView):
    """ remind (via email) everyone about their resolved bugs """

    def remind_resolved_bugs_user(self, user):
        return self._remind_resolved_bugs_user(user)

    def _remind_resolved_bugs_user(self, user):
        """ remind (via email) user to close his resolved bugs """
        LOG(u"Starting email reminder for user %s" % (user.email, ))
        my_bugs_url = self.request.url_for('/bugs/my', resolved=1)
        list_url = self.settings['FRONTEND_PREFIX'] + my_bugs_url

        bugs = Bugs(self.request, user).get_user(resolved=True)
        if not bugs:
            LOG(u"No bugs to remind user %s of" % (user.email, ))
            return self._(u'No bugs for user ${user}', user=user.email)
        output = []
        output.append(self._(u'Hej ${user}! Masz rozwiązane niezamknięte bugi, weź je ogarnij:', user=user.name))
        output.append(u'')
        for i, bug in enumerate(bugs, 1):
            id = bug.id
            desc = bug.desc
            url = bug.url
            output.append(u"%(i)s. #%(id)s %(desc)s %(url)s" % locals())
        output.append(u'')
        output.append(self._(u'Te bugi możesz również zobaczyć pod adresem ${list_url}', list_url=list_url))
        output.append(u'')
        output.append(self._(u'Pozdrawiam,\nTwój intranet'))
        message = u'\n'.join(output)

        topic = self._(u"[intranet] ${num} zgłoszeń do zamknięcia", num=len(bugs))
        with mail.EmailSender() as email_sender:
            email_sender.send(
                user.email,
                topic,
                message,
            )
        LOG(u"Email reminder for user %s started" % (user.email, ))
        return message

    def action(self):
        if Holiday.is_holiday(datetime.date.today()):
            LOG(u"Skipping resolved bugs reminder, because it's a holiday")
            return Response(u"Won't remind")
        LOG(u"Starting resolved bugs reminder")
        for user in User.query.all():
            self._remind_resolved_bugs_user(user)
        LOG(u"Ending resolved bugs reminder")
        return Response(u'Reminded everybody')

