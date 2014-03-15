import copy
import mock

MESSAGE_TEMPLATES = {}
MESSAGE_TEMPLATES['bugzilla'] = (
    '+OK message follows',
    [
        'Return-Path: <developer@stxnext.pl>',
        'Received: from bugzilla.stxnext.pl (thor.stxnext.pl. [178.250.45.112])',
        '        by mx.google.com with ESMTPSA id o43sm20088425eef.12.2014.03.08.06.20.27',
        '        for <developer@stxnext.pl>',
        '        (version=TLSv1 cipher=RC4-SHA bits=128/128);',
        '        Sat, 08 Mar 2014 06:20:27 -0800 (PST)',
        'From: {placeholder_mailer}',
        'To: mailbox@exmaple.com',
        'Subject: [Bug {placeholder_bug_id}] scrum board',
        'Date: Sat, 08 Mar 2014 14:19:54 +0000',
        'X-Bugzilla-Reason: GlobalWatcher',
        'X-Bugzilla-Type: changed',
        'X-Bugzilla-Watch-Reason: None',
        'X-Bugzilla-Product: {placeholder_product}',
        'X-Bugzilla-Component: {placeholder_component}',
        'X-Bugzilla-Version: unspecified',
        'X-Bugzilla-Keywords: ',
        'X-Bugzilla-Severity: normal',
        'X-Bugzilla-Who: {placeholder_login}',
        'X-Bugzilla-Status: NEW',
        'X-Bugzilla-Priority: Normal',
        'X-Bugzilla-Assigned-To: konrad.rotkiewicz@stxnext.pl',
        'X-Bugzilla-Target-Milestone: ---',
        'X-Bugzilla-Flags: ',
        'X-Bugzilla-Changed-Fields: work_time',
        'Message-ID: <bug-904-8-HehYyd6wgV@https.bugzilla.stxnext.pl/>',
        'In-Reply-To: <bug-904-8@https.bugzilla.stxnext.pl/>',
        'References: <bug-904-8@https.bugzilla.stxnext.pl/>',
        'Content-Type: multipart/alternative; boundary="1394288396.c14F0.2224"; charset="UTF-8"',
        'X-Bugzilla-URL: https://bugzilla.stxnext.pl/',
        'Auto-Submitted: auto-generated',
        'MIME-Version: 1.0',
        '', '', '--1394288396.c14F0.2224',
        'Date: Sat, 8 Mar 2014 15:19:56 +0100',
        'MIME-Version: 1.0',
        'Content-Type: text/plain; charset="UTF-8"', '',
        'https://bugzilla.stxnext.pl/show_bug.cgi?id=904',
        '',
        'Konrad Rotkiewicz <konrad.rotkiewicz@stxnext.pl> changed:',
        '',
        '           What    |Removed                     |Added',
        '----------------------------------------------------------------------------',
        '       Hours Worked|                            |{placeholder_time}',
        '',
        '--- Comment #17 from Konrad Rotkiewicz <konrad.rotkiewicz@stxnext.pl> ---',
        'test uwsgi 3', '', '-- ',
        'You are receiving this mail because:',
        'You are watching all bug changes.', '',
        '--1394288396.c14F0.2224',
        'Date: Sat, 8 Mar 2014 15:19:56 +0100',
        'MIME-Version: 1.0',
        'Content-Type: text/html; charset="UTF-8"', '',
        '<html>', '    <head>',
        '      <base href="https://bugzilla.stxnext.pl/" />',
        '    </head>',
        '    <body><span class="vcard"><a class="email" href="mailto:konrad.rotkiewicz&#64;stxnext.pl" title="Konrad Rotkiewicz &lt;konrad.rotkiewicz&#64;stxnext.pl&gt;"> <span class="fn">Konrad Rotkiewicz</span></a>',
        '</span> changed',
        '              <a class="bz_bug_link ',
        '          bz_status_NEW "',
        '   title="NEW - scrum board"',
        '   href="https://bugzilla.stxnext.pl/show_bug.cgi?id=904">bug 904</a>',
        '          <br>',
        '             <table border="1" cellspacing="0" cellpadding="8">',
        '          <tr>', '            <th>What</th>',
        '            <th>Removed</th>',
        '            <th>Added</th>', '          </tr>',
        '',
        '         <tr>',
        '           <td style="text-align:right;">Hours Worked</td>',
        '           <td>', '               &nbsp;',
        '           </td>', '           <td>0.10',
        '           </td>', '         </tr></table>',
        '      <p>', '        <div>',
        '            <b><a class="bz_bug_link ',
        '          bz_status_NEW "',
        '   title="NEW - scrum board"',
        '   href="https://bugzilla.stxnext.pl/show_bug.cgi?id=904#c17">Comment # 17</a>',
        '              on <a class="bz_bug_link ',
        '          bz_status_NEW "',
        '   title="NEW - scrum board"',
        '   href="https://bugzilla.stxnext.pl/show_bug.cgi?id=904">bug 904</a>',
        '              from <span class="vcard"><a class="email" href="mailto:konrad.rotkiewicz&#64;stxnext.pl" title="Konrad Rotkiewicz &lt;konrad.rotkiewicz&#64;stxnext.pl&gt;"> <span class="fn">Konrad Rotkiewicz</span></a>',
        '</span></b>', '        <pre>test uwsgi 3</pre>',
        '        </div>', '      </p>', '      <hr>',
        '      <span>You are receiving this mail because:</span>',
        '      ', '      <ul>',
        '          <li>You are watching all bug changes.</li>',
        '      </ul>', '    </body>', '</html>', '',
        '--1394288396.c14F0.2224--', ''
    ],
    3766,
)


class MailProducer(object):
    DEFAULTS = {
        'bug_id': 1,
        'product': 'PRODUCT',
        'component': 'COMPONENT',
        'login': 'LOGIN',
        'time': 0.1,
        'mailer': 'tracker_mailer@example.com',
    }

    def __init__(self, tracker):
        self._tracker = tracker
        self._tmpl = MESSAGE_TEMPLATES[tracker]


    def _fill(self, **kwargs):
        kwargs = {
            'placeholder_%s' % k: v
            for k, v in kwargs.iteritems()
        }


        tmpl = list(copy.deepcopy(self._tmpl))
        tmpl[1] = [line.format(**kwargs) for line in tmpl[1]]
        return tmpl

    def get(self, **kwargs):
        placeholders = self.DEFAULTS.copy()
        placeholders.update(kwargs)
        msg = self._fill(**placeholders)
        return msg

class POPMock(object):
    def __init__(self, emails_num):
        self.poplib_patch = mock.patch('intranet3.utils.mail_fetcher.poplib')
        self.poplib = None
        self.emails_num = emails_num

    def __enter__(self):
        self.poplib = self.poplib_patch.start()
        conn = self.poplib.POP3_SSL()
        conn.stat.return_value = self.emails_num, None
        producer = MailProducer('bugzilla')
        def retr(i):
            if not hasattr(retr, 'counter'):
                retr.counter = 0
            message = producer.get(
                bug_id=retr.counter,
                login='userx',
                product='PRODUCT_X',
                component='COMPONENT_X',
            )
            retr.counter +=1
            return message
        conn.retr.side_effect = retr

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.poplib = self.poplib_patch.stop()
