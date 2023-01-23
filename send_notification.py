import smtplib
import socket
from email.message import EmailMessage
from pathlib import Path

import config

class NotifyViaMail:
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
        except Exception as err:
            print("\tSign in error: %s" % str(err))

    def send(self, recipient, subject, message, filepath=''):
        msg = EmailMessage()
        msg["From"] = self.username
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.set_content(message)

        if filepath != '':
            path = Path(filepath)
            filename = path.name
            msg.add_attachment(open(path, "r").read(), filename=filename)

        # Sending the mail
        self.smtp.sendmail(self.username, recipient, msg.as_string())
        print(f'message to: {recipient} sent')

    def logout(self):
        self.smtp.quit()

def main():
    mail = NotifyViaMail()
    try:
        mail.login(config.user, config.pwd, config.server_smtp, config.port_smtp)
        mail.send(config.notify, 'hi', 'testing', '/home/drew/desktop/outlook_junk_filter/README.md')
    finally:
        mail.logout()

if __name__ == "__main__":
    main()
