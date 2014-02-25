import smtplib
import mimetypes
from email.utils import formataddr
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.audio import MIMEAudio
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email import encoders

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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.server.close()

    @staticmethod
    def __create_mimeobj(file_path):
        file_name = file_path.split('/')[-1]
        ctype, encoding = mimetypes.guess_type(file_name)
        if ctype is None or encoding is not None:
            # No guess could be made so use a binary type.
            ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)
        if maintype == 'text':
            fp = open(file_path)
            attach = MIMEText(fp.read(), _subtype=subtype)
            fp.close()
        elif maintype == 'image':
            fp = open(file_path, 'rb')
            attach = MIMEImage(fp.read(), _subtype=subtype)
            fp.close()
        elif maintype == 'audio':
            fp = open(file_path, 'rb')
            attach = MIMEAudio(fp.read(), _subtype=subtype)
            fp.close()
        else:
            fp = open(file_path, 'rb')
            attach = MIMEBase(maintype, subtype)
            attach.set_payload(fp.read())
            fp.close()
            # Encode the payload using Base64
            encoders.encode_base64(attach)
        attach.add_header(
            'Content-Disposition',
            'attachment',
            filename=file_name,
        )
        return attach

    def send(self, to, topic, message=None, html_message=None,
             sender_name=None, cc=None, replay_to=None, file_path=None):
        none_provided = (
            message is None and
            html_message is None
        )
        both_provided = (
            message is not None and
            html_message is not None
        )
        if none_provided or both_provided:
            raise TypeError('send() takes either message or html_message')

        email_addr = self.user
        if sender_name:
            email_addr = formataddr((sender_name, self.user))


        # Create the message part
        if message is not None and html_message is None:
            msg = MIMEText(message, "plain", "utf-8")
        elif message is None and html_message is not None:
            msg = MIMEText(html_message, "html", "utf-8")
        else:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(message, "plain"))
            msg.attach(MIMEText(html_message, "html"))

        # Add attachments, if any
        if file_path:
            tmpmsg = msg
            msg = MIMEMultipart()
            msg.attach(tmpmsg)
            msg.attach(self.__create_mimeobj(file_path))

        msg['Subject'] = topic
        msg['From'] = email_addr
        msg['To'] = to
        if cc:
            msg['Cc'] = cc

        if replay_to:
            msg['Reply-To'] = replay_to

        self.server.sendmail(
            self.user,
            to,
            msg.as_string(),
        )


def send(to, topic, message=None, html_message=None,
         sender_name=None, cc=None, replay_to=None, file_path=None):
    """
    Helper for sending single email address
    """
    sender = EmailSender()
    sender.send(
        to,
        topic,
        message,
        html_message,
        sender_name,
        cc,
        replay_to,
        file_path
    )
