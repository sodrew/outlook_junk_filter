import smtplib
import socket
from email.message import EmailMessage
from pathlib import Path

import config

class OutlookSendSmtp:
    def __init__(self):
        self.smtp = None
        self.username = None

    def login(self, username, password, server, port):
        self.username = username
        try:
            self.smtp = smtplib.SMTP(server, port)
            # self.smtp.set_debuglevel(1)
            lhost = socket.gethostname().lower()
            self.smtp.ehlo(lhost)
            self.smtp.starttls()
            self.smtp.ehlo(lhost)
            r, d = self.smtp.login(username, password, initial_response_ok=True)
            assert r == 235, 'login failed: %s' % str(r)
            print("\SMTP Signed in as %s" % self.username)
        except Exception as err:
            print("\tSign in error: %s" % str(err))

    def send(self, recipient, subject, message, filepaths=[]):
        msg = EmailMessage()
        msg["From"] = self.username
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.set_content(message)

        for filepath in filepaths:
            path = Path(filepath)
            filename = path.name
            msg.add_attachment(open(path, "r").read(), filename=filename)

        # Sending the mail
        self.smtp.sendmail(self.username, recipient, msg.as_string())
        print('\t' + f'Message to: {recipient} sent')

    def logout(self):
        self.smtp.quit()

def main():
    mail = OutlookSendSmtp()
    try:
        mail.login(config.user, config.pwd,
                   config.server_smtp, config.port_smtp)
        mail.send(config.notify, 'hi', 'testing',
                  ['./README.md',
                   './LICENSE',])
    finally:
        mail.logout()

if __name__ == "__main__":
    main()
