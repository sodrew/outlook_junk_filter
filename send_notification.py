import smtplib
import socket
from email.message import EmailMessage
from pathlib import Path

import config

class NotifyViaMail:
    def __init__(self):
        self.smtp = None
        self.username = None

    def login(self, username, password):
        self.username = username
        try:
            self.smtp = smtplib.SMTP(config.server_smtp,
                                         config.port_smtp)
            # self.smtp.set_debuglevel(1)
            lhost = socket.gethostname().lower()
            self.smtp.ehlo(lhost)
            self.smtp.starttls()
            self.smtp.ehlo(lhost)
            r, d = self.smtp.login(username, password, initial_response_ok=True)
            assert r == 235, 'login failed: %s' % str(r)
        except Exception as err:
            print("\tSign in error: %s" % str(err))

    def send(self, recipient, subject, message, filepath=''):
        msg = EmailMessage()
        msg["From"] = self.username
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.set_content(message)

        if(filepath != '');
            path = Path(filepath)
            filename = path.name
            msg.add_attachment(open(path, "r").read(), filename=filename)

        # Sending the mail
        self.smtp.sendmail(self.username, recipient, msg.as_string())
        print(f'message to :{recipient} sent')

    def logout(self):
        self.smtp.quit()

from email.message import EmailMessage
def main():
    mail = NotifyViaMail()
    try:
        mail.login(config.user, config.pwd)
        mail.send(config.notify, 'hi', 'testing', '~/desktop/outlook_junk_filter/README.md')
    finally:
        mail.logout()

    # sender = 'somename@outlook.com'
    # recipient = 'somename@gmail.com'

    # msg = EmailMessage()
    # msg.set_content('this is a test')
    # msg['From'] = config.user
    # msg['To'] = config.notify
    # msg['Subject'] = 'test email'

    # with smtplib.SMTP('smtp.office365.com', 587) as server:
    #     server.set_debuglevel(1)
    #     server.ehlo('lowercasehost')
    #     server.starttls()
    #     server.ehlo('lowercasehost')
    #     server.login(config.user, config.pwd)
    #     server.sendmail(config.user, config.notify, msg.as_string())
    #     print('Email sent!')
    #     server.close()
if __name__ == "__main__":
    main()
