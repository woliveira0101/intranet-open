# -*- coding: utf-8 -*-
"""
Sending emails
"""
import re
import email
import quopri
import datetime
import time
import poplib
from base64 import b64decode
from pprint import pformat
from email.header import decode_header
from email.utils import parsedate

import transaction
from intranet3.models import ApplicationConfig, Project, Tracker, TrackerCredentials, DBSession
from intranet3.models.project import SelectorMapping
from intranet3.log import DEBUG_LOG, WARN_LOG, EXCEPTION_LOG, INFO_LOG
from intranet3.utils.timeentry import add_time

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)
WARN = WARN_LOG(__name__)
DEBUG = DEBUG_LOG(__name__)

MIN_HOURS = 6.995 #record hours

decode = lambda header: u''.join(
    val.decode('utf-8' if not encoding else encoding)
        for val, encoding in decode_header(header)
).strip()

Q_ENCODING_REGEXP = re.compile(r'(\=\?[^\?]+\?[QB]\?[^\?]+\?\=)')

def decode_subject(val):
    for value in Q_ENCODING_REGEXP.findall(val):
        val = val.replace(value, decode(value))
    return val.strip()

def get_msg_payload(msg):
    encoding = msg.get('Content-Transfer-Encoding')
    payload = msg.get_payload()
    if type(payload) == list:
        a_msg = payload[0] # first is plaintext, second - html
        encoding = a_msg.get('Content-Transfer-Encoding')
        payload = a_msg.get_payload()
    DEBUG(u'Extracted email msg %r with encoding %r' % (payload, encoding))
    if encoding == 'quoted-printable':
        payload = quopri.decodestring(payload)
    elif encoding == 'base64':
        payload = b64decode(payload)
    return payload


class TimeEntryMailExtractor(object):
    """
    Extracts timeentry from mail
    """
    SUBJECT_REGEXP = re.compile(r'^\[Bug (\d+)\](.*)')
    HOURS_REGEXP = re.compile(r'^\s*Hours Worked\|\s*\|(\d+(\.\d+)?)$')
    HOURS_NEW_BUG_REGEXP = re.compile(r'^\s*Hours Worked: (\d+(\.\d+)?)$')

    TRAC_SUBJECT_REGEXP = re.compile(r'^(Re\:\ +)?\[.+\] \#\d+\: (.*)')
    TRAC_HOURS_REGEXP = re.compile(r'.*Add Hours to Ticket:\ *(\d+(\.\d+)?)')
    TRAC_AUTHOR_REGEXP = re.compile(r'^Changes \(by (.*)\)\:')
    TRAC_COMPONENT_REGEXP = re.compile(r'.*Component:\ *([^|]*)')

    def __init__(self, trackers, logins_mappings, projects, selector_mappings):
        self.trackers = trackers
        self.logins_mappings = logins_mappings
        self.projects = projects
        self.selector_mappings = selector_mappings

    def handle_trac_email(self, msg, tracker):
        date = decode(msg['Date'])
        subject = msg['Subject']
        DEBUG(u'Message with subject %r retrieved from date %r' % (subject, date))

        date = datetime.datetime.fromtimestamp(time.mktime(parsedate(date)))

        bug_id = decode(msg['X-Trac-Ticket-ID'])

        subject = decode(subject.replace('\n', u''))
        match = self.TRAC_SUBJECT_REGEXP.match(subject)
        if not match:
            WARN(u"Trac subject not matched %r" % (subject, ))
            return
        subject = match.group(2)

        hours = 0.0
        who = ''
        component = ''
        payload = get_msg_payload(msg)

        for line in payload.split('\n'):
            match = self.TRAC_HOURS_REGEXP.match(line)
            if match:
                hours = float(match.group(1))
                continue
            match = self.TRAC_AUTHOR_REGEXP.match(line)
            if match:
                who = match.group(1)
                continue
            match = self.TRAC_COMPONENT_REGEXP.match(line)
            if match:
                component = match.group(1).strip()
                continue

        DEBUG(u'Found bug title %(subject)s component %(component)s, by %(who)s from %(date)s, hours %(hours)s' % locals())

        if hours <= 0.0:
            DEBUG(u"Ignoring bug with no hours")
            return

        who = who.lower()
        if not who in self.logins_mappings[tracker.id]:
            DEBUG(u'User %s not in logins mapping' % (who, ))
            return

        user = self.logins_mappings[tracker.id][who]
        DEBUG(u'Found user %s' % (user.name, ))

        mapping = self.selector_mappings[tracker.id]
        project_id = mapping.match(bug_id, 'none', component)

        if project_id is None:
            DEBUG(u'Project not found for component %s' % (component, ))
            return
        project = self.projects[project_id]

        LOG(u"Will add entry for user %s project %s bug #%s hours %s title %s" % (
            user.name, project.name, bug_id, hours, subject
            ))

        return user.id, date, bug_id, project_id, hours, subject

    def handle_bugzilla_email(self, msg, tracker):
        date = decode(msg['Date'])
        component = decode(msg['X-Bugzilla-Component'])
        product = decode(msg['X-Bugzilla-Product'])
        who = decode(msg['X-Bugzilla-Who'])
        subject = msg['Subject']
        DEBUG(u'Message with subject %r retrieved from date %r' % (subject, date))

        date = datetime.datetime.fromtimestamp(time.mktime(parsedate(date)))

        subject = decode_subject(subject.replace('\n', u'').replace(u':', u' '))
        match = self.SUBJECT_REGEXP.match(subject)
        if not match:
            DEBUG(u"Subject doesn't match regexp: %r" % subject)
            return
        bug_id, subject = match.groups()
        subject = subject.strip()
        is_new_bug = subject.startswith('New ')
        payload = get_msg_payload(msg)

        username = who.lower()
        if username not in self.logins_mappings[tracker.id]:
            DEBUG(u'User %s not in logins mapping' % (who, ))
            return


        DEBUG(u'Found bug title %(subject)s product %(product)s, component %(component)s, by %(who)s from %(date)s' % locals())

        bug_id = int(bug_id)

        newline = '\n'
        # some emails have \r\n insted of \n
        if '\r\n' in payload:
            DEBUG(u'Using CRLF istead of LF')
            newline = '\r\n'

        for line in payload.split(newline):
            if is_new_bug:
                match = self.HOURS_NEW_BUG_REGEXP.match(line)
            else:
                match = self.HOURS_REGEXP.match(line)
            if match:
                hours = float(match.groups()[0])
                break
        else:
            hours = 0.0

        DEBUG(u'Found bug #%(bug_id)s with title %(subject)s product %(product)s, component %(component)s, by %(who)s, hours %(hours)f %(date)s' % locals())
        if is_new_bug:
            # new bug - create with 0 h, first strip title
            subject = subject[4:].strip()
            DEBUG(u'Bug creation found %s' % (subject, ))
        elif hours == 0.0:
            DEBUG(u'Ignoring non-new bug without hours')
            return

        user = self.logins_mappings[tracker.id][username]
        DEBUG(u'Found user %s' % (user.name, ))
        # selector_mapping given explicitly to avoid cache lookups
        mapping = self.selector_mappings[tracker.id]
        project_id = mapping.match(bug_id, product, component)
        project = self.projects[project_id]

        LOG(u"Will add entry for user %s project %s bug #%s hours %s title %s" % (
            user.name, project.name, bug_id, hours, subject
            ))

        return user.id, date, bug_id, project_id, hours, subject

    handle_cookie_trac_email = handle_trac_email
    handle_igozilla_email = handle_bugzilla_email
    handle_rockzilla_email = handle_bugzilla_email

    def match_tracker(self, msg):
        sender = decode(msg['From'])
        for email in self.trackers:
            if email in sender:
                return self.trackers[email]
        else:
            return None

    def get(self, msg):
        """ When single message was retrieved """
        sender = decode(msg['From'])
        tracker = self.match_tracker(msg)
        if tracker is None:
            DEBUG(u'Email from %s ignored, no tracker matched' % (sender, ))
            return

        # find appopriate handler
        handler = getattr(self, 'handle_%s_email' % tracker.type)
        # handler should parse the response and return essential info or None
        data = handler(msg, tracker)
        if data is None: # email should be ignored
            return
        user_id, date, bug_id, project_id, hours, subject = data
        return add_time(user_id, date, bug_id, project_id, hours, subject)


class MailFetcher(object):

    HOST = 'pop.gmail.com'
    MAX_EMAILS = 100

    def __init__(self, login, password, trackers, logins_mappings, projects, selector_mappings):
        self.login = login
        self.password = password
        self.trackers = trackers
        self.logins_mappings = logins_mappings
        self.projects = projects
        self.selector_mappings = selector_mappings

    def __iter__(self):
        pop_conn = poplib.POP3_SSL(self.HOST)
        pop_conn.user(self.login)
        pop_conn.pass_(self.password)

        stats = pop_conn.stat()
        LOG(u'Emails: %s' % (pformat(stats)))
        num, _ = stats
        num = num if num < self.MAX_EMAILS else self.MAX_EMAILS

        messages = (pop_conn.retr(i) for i in range(1, num + 1))
        messages = ("\n".join(mssg[1]) for mssg in messages)
        messages = (email.parser.Parser().parsestr(mssg) for mssg in messages)
        for msg in messages:
            yield msg

        pop_conn.quit()

class MailCheckerTask(object):

    def __call__(self, *args, **kwargs):
        config = ApplicationConfig.get_current_config(allow_empty=True)
        if config is None:
            WARN(u'Application config not found, emails cannot be checked')
            return
        trackers = dict(
            (tracker.mailer, tracker)
                for tracker in Tracker.query.filter(Tracker.mailer != None).filter(Tracker.mailer != '')
        )
        if not len(trackers):
            WARN(u'No trackers have mailers configured, email will not be checked')
            return

        username = config.google_user_email.encode('utf-8')
        password = config.google_user_password.encode('utf-8')

        # TODO
        logins_mappings = dict(
            (tracker.id, TrackerCredentials.get_logins_mapping(tracker))
                for tracker in trackers.itervalues()
        )
        selector_mappings = dict(
            (tracker.id, SelectorMapping(tracker))
                for tracker in trackers.itervalues()
        )

        # find all projects connected to the tracker
        projects = dict(
            (project.id, project)
                for project in Project.query.all()
        )

        # all pre-conditions should be checked by now

        # start fetching
        fetcher = MailFetcher(
            username,
            password,
            trackers,
            logins_mappings,
            projects,
            selector_mappings,
        )
        # ok, we have all mails, lets create timeentries from them
        extractor = TimeEntryMailExtractor(
            trackers,
            logins_mappings,
            projects,
            selector_mappings,
        )

        for msg in fetcher:
            timeentry = extractor.get(msg)
            if timeentry:
                DBSession.add(timeentry)
        transaction.commit()

