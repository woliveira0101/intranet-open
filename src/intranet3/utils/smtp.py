from email.utils import formataddr
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email import Encoders

from intranet3.models import ApplicationConfig
from intranet3.log import DEBUG_LOG, WARN_LOG, EXCEPTION_LOG, INFO_LOG

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)
WARN = WARN_LOG(__name__)
DEBUG = DEBUG_LOG(__name__)


class EmailSender(object):

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
