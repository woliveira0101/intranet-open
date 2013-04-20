from twisted.mail.smtp import ESMTPSenderFactory
from twisted.mail.imap4 import IClientAuthentication
from twisted.mail.smtp import ESMTPSender, ESMTPSenderFactory
from zope.interface import implements


class XOAUTH2Authenticator:
    implements(IClientAuthentication)

    def __init__(self, user):
        self.user = user

    def getName(self):
        return "XOAUTH2"

    def challengeResponse(self, access_token, chal=None):
        return 'user=%s\1auth=Bearer %s\1\1' % (self.user, access_token)


class ESMTP_XOAUTH2_Sender(ESMTPSender):
    def _registerAuthenticators(self):
        self.registerAuthenticator(XOAUTH2Authenticator(self.username))


class ESMTP_XOUATH2_SenderFactory(ESMTPSenderFactory):
    protocol = ESMTP_XOAUTH2_Sender

