# -*- coding: utf-8 -*-
"""
Sending emails
"""
import re
import email
import quopri
import datetime
import time
from base64 import b64decode
from functools import partial
from pprint import pformat
from email.header import decode_header
from email.utils import parsedate, formataddr
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email import Encoders

from twisted.internet import ssl, reactor
from twisted.internet.defer import Deferred, DeferredList
from twisted.mail.smtp import ESMTPSenderFactory
from twisted.mail.pop3client import POP3Client
from twisted.internet.protocol import ClientFactory

from intranet3.models import ApplicationConfig, Project, Tracker, TrackerCredentials
from intranet3.models.project import SelectorMapping
from intranet3.log import DEBUG_LOG, WARN_LOG, EXCEPTION_LOG, INFO_LOG
from intranet3.utils.timeentry import add_time

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
from email.mime.text import MIMEText

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)
WARN = WARN_LOG(__name__)
DEBUG = DEBUG_LOG(__name__)

MIN_HOURS = 6.995 #record hours

class EmailSender(object):

    SMTP_SERVER = 'smtp.gmail.com'
    SMTP_PORT = 587
    contextFactory = ssl.ClientContextFactory()

    @classmethod
    def send(cls, to, topic, message, sender_name=None, cc=None, replay_to=None):
        """
        Send an email with message to given address.
        This is an asynchronous call.

        @return: deferred
        """
        config = ApplicationConfig.get_current_config()
        user = config.google_user_email
        email_addr = user
        if sender_name:
            email_addr = formataddr((sender_name, email_addr))
        secret = config.google_user_password
        SenderFactory = ESMTPSenderFactory

        email = MIMEText(message, _charset='utf-8')
        email['Subject'] = topic
        email['From'] = email_addr
        email['To'] = to
        if cc:
            email['Cc'] = cc

        if replay_to:
            email['Reply-To'] = replay_to

        formatted_mail = email.as_string()

        messageFile = StringIO(formatted_mail)

        resultDeferred = Deferred()

        senderFactory = SenderFactory(
            user, # user
            secret, # secret
            user, # from
            to, # to
            messageFile, # message
            resultDeferred, # deferred
            contextFactory=cls.contextFactory)

        reactor.connectTCP(cls.SMTP_SERVER, cls.SMTP_PORT, senderFactory)
        return resultDeferred

    @classmethod
    def send_html(cls, to, topic, message):
        config = ApplicationConfig.get_current_config()

        email = MIMEMultipart('alternative')
        email['Subject'] = topic
        email['From'] = config.google_user_email
        email['To'] = to
        email.attach(MIMEText(message,'html', 'utf-8'))

        formatted_mail = email.as_string()

        messageFile = StringIO(formatted_mail)

        resultDeferred = Deferred()

        senderFactory = ESMTPSenderFactory(
            config.google_user_email, # user
            config.google_user_password, # secret
            config.google_user_email, # from
            to, # to
            messageFile, # message
            resultDeferred, # deferred
            contextFactory=cls.contextFactory)

        reactor.connectTCP(cls.SMTP_SERVER, cls.SMTP_PORT, senderFactory)
        return resultDeferred

    @classmethod
    def send_with_file(cls, to, topic, message, file_path):
        config = ApplicationConfig.get_current_config()

        email = MIMEMultipart()
        email['Subject'] = topic
        email['From'] = config.google_user_email
        email['To'] = to

        part = MIMEBase('application', "octet-stream")
        part.set_payload(open(file_path, "rb").read())
        Encoders.encode_base64(part)

        part.add_header('Content-Disposition', 'attachment; filename="%s"' % file_path.split('/')[-1])

        email.attach(part)
        email.attach(MIMEText(message))

        formatted_mail = email.as_string()

        messageFile = StringIO(formatted_mail)

        resultDeferred = Deferred()

        senderFactory = ESMTPSenderFactory(
            config.google_user_email, # user
            config.google_user_password, # secret
            config.google_user_email, # from
            to, # to
            messageFile, # message
            resultDeferred, # deferred
            contextFactory=cls.contextFactory)

        reactor.connectTCP(cls.SMTP_SERVER, cls.SMTP_PORT, senderFactory)
        return resultDeferred



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

class MailerPOP3Client(POP3Client):

    MAX_EMAILS = 100

    SUBJECT_REGEXP = re.compile(r'^\[Bug (\d+)\](.*)')
    HOURS_REGEXP = re.compile(r'^\s*Hours Worked\|\s*\|(\d+(\.\d+)?)$')
    HOURS_NEW_BUG_REGEXP = re.compile(r'^\s*Hours Worked: (\d+(\.\d+)?)$')

    TRAC_SUBJECT_REGEXP = re.compile(r'^(Re\:\ +)?\[.+\] \#\d+\: (.*)')
    TRAC_HOURS_REGEXP = re.compile(r'.*Add Hours to Ticket:\ *(\d+(\.\d+)?)')
    TRAC_AUTHOR_REGEXP = re.compile(r'^Changes \(by (.*)\)\:')
    TRAC_COMPONENT_REGEXP = re.compile(r'.*Component:\ *([^|]*)')

    timeout = 10

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
        if not who in self.factory.logins_mappings[tracker.id]:
            DEBUG(u'User %s not in logins mapping' % (who, ))
            return

        user = self.factory.logins_mappings[tracker.id][who]
        DEBUG(u'Found user %s' % (user.name, ))

        mapping = self.factory.selector_mappings[tracker.id]
        project_id = mapping.match(bug_id, 'none', component)

        if project_id is None:
            DEBUG(u'Project not found for component %s' % (component, ))
            return
        project = self.factory.projects[project_id]

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
        if username not in self.factory.logins_mappings[tracker.id]:
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

        user = self.factory.logins_mappings[tracker.id][username]
        DEBUG(u'Found user %s' % (user.name, ))
        # selector_mapping given explicitly to avoid cache lookups
        mapping = self.factory.selector_mappings[tracker.id]
        project_id = mapping.match(bug_id, product, component)
        project = self.factory.projects[project_id]

        LOG(u"Will add entry for user %s project %s bug #%s hours %s title %s" % (
            user.name, project.name, bug_id, hours, subject
            ))

        return user.id, date, bug_id, project_id, hours, subject

    handle_cookie_trac_email = handle_trac_email
    handle_igozilla_email = handle_bugzilla_email
    handle_rockzilla_email = handle_bugzilla_email

    def serverGreeting(self, greeting):
        """ When connected to server """
        DEBUG(u'Server greeting received %s' % (pformat(greeting, )))
        self.login(self.factory.login, self.factory.password)\
        .addCallbacks(self.on_login, partial(self.fail, u'login'))

    def on_login(self, welcome):
        """ When login succeeded """
        DEBUG(u'Logged in: %s' % (welcome, ))
        self.stat().addCallbacks(self.on_stat, partial(self.fail, u'stat'))

    def prepare(self):
        """ Prepare structures for bugs fetching """
        self.times = []

    def on_stat(self, stats):
        """ When number of messages was provided """
        LOG(u'Emails: %s' % (pformat(stats)))
        mails, sizes = stats
        if mails > self.MAX_EMAILS:
            mails = self.MAX_EMAILS
        if mails:
            self.prepare()

            retrievers = []
            for i in xrange(mails):
                d = self.retrieve(i)
                d.addCallbacks(self.on_retrieve, partial(self.fail, u'retrive %s' % (i, )))
                retrievers.append(d)
            DeferredList(retrievers).addCallback(self.on_finish)
        else:
            DEBUG(u'No new messages')
            self.quit().addCallbacks(self.on_quit, partial(self.fail, u'empty quit'))

    def match_tracker(self, msg):
        sender = decode(msg['From'])
        for email in self.factory.trackers:
            if email in sender:
                return self.factory.trackers[email]
        else:
            return None

    def on_retrieve(self, lines):
        """ When single message was retrieved """
        msg = email.message_from_string('\n'.join(lines))
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
        add_time(user_id, date, bug_id, project_id, hours, subject)


    def on_finish(self, results):
        """ When all messages have been retrieved """
        self.quit().addCallbacks(self.on_quit, partial(self.fail, u'quit'))

    def on_quit(self, bye):
        """ When QUIT finishes """
        DEBUG(u'POP3 Quit: %s' % bye)
        self.factory.done_callback()

    def fail(self, during, resp):
        """ Something went wrong """
        EXCEPTION(u'POP3 Client failed during %s: %s' % (during, pformat(resp)))
        self.factory.done_callback()

class CustomClientFactory(ClientFactory):

    protocol = MailerPOP3Client

    def __init__(self, login, password, done_callback, trackers, logins_mappings, projects, selector_mappings):
        self.login = login
        self.password = password
        self.done_callback = done_callback
        self.trackers = trackers
        self.logins_mappings = logins_mappings
        self.projects = projects
        self.selector_mappings = selector_mappings

class MailCheckerTask(object):

    MAX_BUSY_CALLS = 3
    POP3_SERVER = 'pop.gmail.com'
    POP3_PORT = 995
    context_factory = ssl.ClientContextFactory()

    def __init__(self):
        self.busy = False
        self.busy_calls = 0

    def __call__(self):
        if self.busy:
            self.busy_calls += 1
            if self.busy_calls > self.MAX_BUSY_CALLS:
                self.busy_calls = 0
                WARN(u'Will override a busy Mail Checker')
                self.run()
            else:
                WARN(u'Mail Checker is already running, ignoring (%s/%s)' % (self.busy_calls, self.MAX_BUSY_CALLS))
        else:
            self.busy_calls = 0
            self.busy = True
            LOG(u'Will start Mail Checker')
            self.run()

    def mark_not_busy(self):
        if not self.busy:
            WARN(u'Tried to unmark an already unmarked Mail Checker')
        else:
            self.busy = False
            LOG(u'Marked Mail Check as not busy anymore')

    def run(self):
        self._run()

    def _run(self):
        config = ApplicationConfig.get_current_config(allow_empty=True)
        if config is None:
            WARN(u'Application config not found, emails cannot be checked')
            return self.mark_not_busy()
        trackers = dict(
            (tracker.mailer, tracker)
                for tracker in Tracker.query.filter(Tracker.mailer != None).filter(Tracker.mailer != '')
        )
        if not len(trackers):
            WARN(u'No trackers have mailers configured, email will not be checked')
            return self.mark_not_busy()

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
        f = CustomClientFactory(username, password, self.mark_not_busy,
            trackers, logins_mappings, projects, selector_mappings)
        f.protocol = MailerPOP3Client
        reactor.connectSSL(self.POP3_SERVER, self.POP3_PORT, f, self.context_factory)

