from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import config
import ssl

class NotifyViaMail:
    def __init__(self):
        self.smtp = None
        self.username = None

    def login(self, username, password):
        self.username = username
        try:
            self.smtp = smtplib.SMTP(config.server_smtp,
                                         config.port_smtp)
            self.smtp.set_debuglevel(1)
            self.smtp.ehlo('mylowercasehost')
            self.smtp.starttls()
            self.smtp.ehlo('mylowercasehost')
            r, d = self.smtp.login(username, password, initial_response_ok=True)
            # self.smtp.ehlo()
            print("\tSMTP Signed in as %s" % self.username)
        except Exception as err:
            print("\tSign in error: %s" % str(err))

    def send(self, recipient, subject, msg_text, msg_html=''):
        # Instance of MIMEMultipart
        msg = MIMEMultipart("alternative")

        # Write the subject
        msg["Subject"] = subject

        msg["From"] = self.username
        msg["To"] = recipient

        # Attach the Plain body with the msg instance
        msg.attach(MIMEText(msg_text, "plain"))

        if(msg_html == ''):
            msg_html = '<p>'+msg_text+'</p>'

        # Attach the HTML body with the msg instance
        msg.attach(MIMEText(msg_html, "html"))

        # Sending the mail
        self.smtp.sendmail(self.username, recipient, msg.as_string())
        print('message to :{recipient} sent')

    def logout(self):
        self.smtp.quit()

from email.message import EmailMessage
def main():
    # mail = NotifyViaMail()
    # try:
    #     mail.login(config.user, config.pwd)
    #     mail.send(config.notify, 'hi', 'testing')
    # finally:
    #     mail.logout()

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
