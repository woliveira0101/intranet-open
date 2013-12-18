import smtplib
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
    HOST = 'smtp.gmail.com'
    PORT = 587

    def __init__(self):
        config = ApplicationConfig.get_current_config()
        user = config.google_user_email
        secret = config.google_user_password
        self.user, self.secret = user, secret
        self.server = smtplib.SMTP(self.HOST, self.PORT)
        self.server.ehlo()
        self.server.starttls()
        self.server.login(user, secret)

    def send(self, to, topic, message=None, html_message=None,
             sender_name=None, cc=None, replay_to=None):

        email_addr = self.user
        if sender_name:
            email_addr = formataddr((sender_name, self.user))

        email = MIMEText(message, _charset='utf-8')
        email['Subject'] = topic
        email['From'] = email_addr
        email['To'] = to
        if cc:
            email['Cc'] = cc

        if replay_to:
            email['Reply-To'] = replay_to

        self.server.sendmail(
            self.user,
            to,
            email.as_string(),
        )

    def send_html(self, to, topic, message):
        config = ApplicationConfig.get_current_config()

        email = MIMEMultipart('alternative')
        email['Subject'] = topic
        email['From'] = config.google_user_email
        email['To'] = to
        email.attach(MIMEText(message, 'html', 'utf-8'))

        self.server.sendmail(
            self.user,
            to,
            email.as_string(),
        )

    def send_with_file(self, to, topic, message, file_path):
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

        self.server.sendmail(
            self.user,
            to,
            email.as_string(),
        )
