import base64
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from imaplib import IMAP4, IMAP4_SSL, Time2Internaldate
from smtplib import SMTP, SMTPAuthenticationError, SMTPSenderRefused
from celery.app.utils import Settings

from celery.utils.log import get_task_logger
from mongoengine.errors import DoesNotExist

from nightowl.models import admin as admin_model
from nightowl.utils.datetime import utc_now
from nightowl.utils.security import decrypt
from nightowl.utils.timer import set_timer
from nightowl.worker import app


logger = get_task_logger(__name__)


class IMAPError(Exception):
    pass


class DelayNotification:
    _cache = {}

    # handler's first arg must be to_addr and second arg must be a list
    def __init__(self, to_addr, handler, delay=10, key=None):
        self.to_addr = to_addr
        self.handler = handler
        self.delay = delay
        if key is None:
            self.key = (to_addr, handler.__name__)
        else:
            self.key = (to_addr, key)

    def _send(self):
        values = self._cache[self.key]
        self.handler(self.to_addr, values)
        self._cache.pop(self.key)

    def send(self, values):
        if self.key not in self._cache:
            self._cache[self.key] = []
        if isinstance(values, list):
            self._cache[self.key].extend(values)
        else:
            self._cache[self.key].append(values)
        set_timer(self.key, self.delay, self._send)


class EmailStyle:
    style = {
        'bg_color': '#F6F6F6',
        'primary_color': '#EB6100',
        'secondary_color': '#FDEFE6',
        'text_color': '#606266',
    }


class EmailMessage(EmailStyle):

    def __init__(self, message='', style=None):
        if style is not None:
            self.style = self.style.update(self.style)
        self.message = message

    def __str__(self):
        if not self.message:
            return '<br>'
        return f'<p class="normaltext">{self.message}</p>'


class EmailTable(EmailStyle):

    def __init__(self, header, rows, style=None):
        if style is not None:
            self.style = self.style.update(self.style)
        self.header = header
        self.rows = rows

    def __str__(self):
        header_tr = self.generate_header()
        row_trs = ''.join([self.generate_row(row) for row in self.rows])
        return f'''<table border="0">
            {header_tr}
            {row_trs}
        </table>'''

    def generate_header(self):
        len_headers = len(self.header)
        th_list = []
        for index, header in enumerate(self.header):
            if index == 0:
                th_list.append(
                    f'<th bgcolor="{self.style["secondary_color"]}" '
                    f'style="border-left: 1px solid {self.style["primary_color"]}">{header}</td>')
            elif index == len_headers - 1:
                th_list.append(
                    f'<th bgcolor="{self.style["secondary_color"]}"'
                    f'style="border-right: 1px solid {self.style["primary_color"]}">{header}</th>')
            else:
                th_list.append(f'<th bgcolor="{self.style["secondary_color"]}">{header}</th>')
        return f'<tr>{"".join(th_list)}</tr>'

    def generate_row(self, row, full_span=False):
        td_list = []
        for index, cell in enumerate(row):
            if cell is None:
                cell = ''
            if index == 0:
                td_list.append(
                    f'<td style="border-left:1px solid {self.style["text_color"]}">{cell}</td>')
            else:
                td_list.append(f'<td>{cell}</td>')
        return f'<tr>{"".join(td_list)}</tr>'


class EmailButton(EmailStyle):

    def __init__(self, text, link, style=None):
        if style is not None:
            self.style = self.style.update(self.style)
        self.text = text
        self.link = link

    def __str__(self):
        return f'''<div>
            <!--[if mso]>
                <v:roundrect
                    xmlns:v="urn:schemas-microsoft-com:vml"
                    xmlns:w="urn:schemas-microsoft-com:office:word"
                    href="{self.link}"
                    style="height:36px;v-text-anchor:middle;width:200px;line-height:36px;"
                    arcsize="10%" strokecolor="{self.style["primary_color"]}"
                    fillcolor="{self.style["secondary_color"]}">
                    <w:anchorlock/>
                    <center style="color:{self.style["primary_color"]};
                        font-family:Calibri,"Microsoft YaHei";
                        font-size:14px;font-weight:bold;">{self.text}</center>
                </v:roundrect>
            <![endif]-->
            <a href="{self.link}">{self.text}</a>
        </div>'''


class EmailHtml(EmailStyle):

    def __init__(self, *messages, style=None):
        if style is not None:
            self.style = self.style.update(self.style)
        self.messages = messages

    def __str__(self):
        return f'''<html>
            <head>
            <style type="text/css">
            html,body {{
                font-family: Calibri,"Microsoft YaHei";
                font-size: 14px;
            }}
            p.normaltext {{ margin: 0; }}
            table {{ border-collapse: collapse; }}
            th {{
                width: 140;
                height: 26;
                border-top: 1px solid {self.style["primary_color"]};
                border-bottom: 1px solid {self.style["primary_color"]};
                border-right: 1px solid {self.style["primary_color"]};
                color: {self.style["primary_color"]};
            }}
            td {{
                height: 24;
                text-align: center;
                border-right: 1px solid {self.style["text_color"]};
                border-bottom: 1px solid {self.style["text_color"]};
                color: {self.style["text_color"]};
            }}
            </style>
            </head>
            <body>
                {'        '.join([str(message) for message in self.messages])}
            </body>
        </html>'''


def _send_email(to_addr, subject, content, format='html',
                email_settings=None, cc=None, bcc=None, attachments=None):
    if not email_settings:
        settings = admin_model.EmailSettings.fetch()
        if not settings:
            raise ValueError('Failed to get Email settings')
        host = settings.host
        port = settings.port
        auth_type = settings.auth_type
        email_addr = settings.email
        password = decrypt(settings.password, settings.salt)
    else:
        host = email_settings['host']
        port = email_settings['port']
        auth_type = email_settings['auth_type']
        email_addr = email_settings['email']
        password = email_settings['password']

    if not email_addr or not password:
        raise ValueError("'email' and 'password' must be set")

    if attachments is None:
        attachments = []

    main_msg = MIMEMultipart()
    main_msg['From'] = formataddr(('NightOwl Network Development Platform', email_addr))
    main_msg['To'] = formataddr(('', to_addr))
    main_msg['Subject'] = Header(subject, 'utf-8')
    if cc is not None:
        cc_list = []
        for cc_addr in cc:
            cc_list.append(formataddr(('', cc_addr)))
        main_msg['Cc'] = ','.join(cc_list)
    if bcc is not None:
        bcc_list = []
        for bcc_addr in bcc:
            bcc_list.append(formataddr(('', bcc_addr)))
        main_msg['Bcc'] = ','.join(bcc_list)
    text_msg = MIMEText(content, format, 'utf-8')
    main_msg.attach(text_msg)

    for filename, attachment in attachments:
        if isinstance(attachment, str):
            attachment = base64.b64decode(attachment.encode())
        file_msg = MIMEApplication(attachment, 'octet-stream')
        file_msg.add_header('Content-Disposition', 'attachment', filename=filename)
        main_msg.attach(file_msg)

    with SMTP(host, port) as smtp_server:
        if auth_type in ('SSL', 'TLS'):
            smtp_server.starttls()
        smtp_server.login(email_addr, password)
        smtp_server.send_message(main_msg)

    try:
        imap = IMAP4_SSL if auth_type in ('SSL', 'TLS') else IMAP4
        with imap(host, 993) as imap_server:
            imap_server.login(email_addr, password)
            imap_server.append(
                '&XfJT0ZABkK5O9g-', '\\Seen',
                Time2Internaldate(utc_now()), main_msg.as_bytes())
    except Exception as ex:
        raise IMAPError(str(ex)) from ex


@app.task(bind=True, rate_limit='25/m', ignore_result=True, max_retries=None)
def send_email(self, to_addr, subject, content, format='html',
               email_settings=None, cc=None, bcc=None, attachments=None):
    try:
        _send_email(to_addr, subject, content, format,
                    email_settings, cc, bcc, attachments)
    except SMTPSenderRefused as ex:
        logger.warning(
            'Failed to send Email, will retry in 1 minute ('
            f'to_addr={to_addr}, error={ex})')
        raise self.retry(exc=ex, countdown=60)
    except SMTPAuthenticationError as ex:
        logger.error(
            'Failed to send Email, will retry in 10 minutes ('
            f'to_addr={to_addr}, error={ex})')
        raise self.retry(exc=ex, countdown=600)
    except IMAPError as ex:
        logger.error(f'Failed to save Email (to_addr={to_addr}, error={ex})')
    except Exception as ex:
        logger.error(
            'Failed to send Email, will retry in 60 minutes ('
            f'to_addr={to_addr}, error={ex})')
        raise self.retry(exc=ex, countdown=3600)
