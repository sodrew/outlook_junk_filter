import os
import requests
import re
import tqdm
from datetime import date
from unidecode import unidecode
import junk_keywords
from msal import PublicClientApplication, SerializableTokenCache
from pprint import pprint
import argparse
import traceback
import logging
logger = logging.getLogger("junkconfig")

import config
from msgraphapi import MSGraphAPI
from persistence import Persistence

class OutlookJunkFilter:
    def __init__(self):
        self.msgraphapi = MSGraphAPI()
        self.msgraphapi.authenticate()
        self.persist = Persistence(self.msgraphapi)
        logger.debug("Initialized GraphAPIJunkFilter")

    def get_fingerprint_from_headers(self, headers):
        ip = None
        dkim_domain = None
        from_address = None

        for h in headers:
            name = h['name'].lower()
            value = h['value']

            if name == 'authentication-results':
                match = re.search(r'sender IP is ([\d.]+)', value)
                if match:
                    ip = match.group(1)
            elif name == 'dkim-signature':
                match = re.search(r'd=([^;]+)', value)
                if match:
                    dkim_domain = match.group(1)
            elif name == 'from':
                match = re.search(r'<(.+?)>', value)
                if match:
                    from_address = match.group(1)

        logger.debug(f"Sender IP   : {ip}")
        logger.debug(f"DKIM domain : {dkim_domain}")
        logger.debug(f"From address: {from_address}")
        return {'ip':ip, 'dkim':dkim_domain, 'from':from_address}

    def get_junk_emails(self):
        """
        Retrieve emails from the Junk Email folder.
        """
        logger.info('retrieving junk email')

        base = 'mailFolders/JunkEmail/messages'
        count = 50
        fields = [
            'subject',
            'from',
            'sender',
            'internetMessageHeaders',
            ]
        order = 'receivedDateTime asc'

        url = f"{base}?$top={count}&$orderby={order}&$select={','.join(fields)}"
        all_messages = []
        while url:
            data = self.msgraphapi.get_api(url)

            # ✅ Get nextLink BEFORE deleting anything
            next_link = data.get('@odata.nextLink')
            messages = data.get('value', [])
            logging.info(f'got {len(messages)} messages')

            for msg in messages:
                msg_id = msg['id']
                subject = msg.get('subject', '(no subject)')
                logging.debug(f'\t: {subject}')

                headers = msg.get('internetMessageHeaders', [])
                fp = self.get_fingerprint_from_headers(headers)
                msg['fp'] = fp

                all_messages.append(msg)

            if url == next_link:
                break

            url = next_link

        return all_messages

    def delete_emails(self, email_ids):
        """
        Delete emails by ID using batch requests.
        """
        self.msgraphapi.batch_delete_msgs(email_ids)

    def send_report(self, junk_uids, kept_msgs):
        # Prepare summary
        report = (
            f"Outlook Junk Filter - {str(date.today())}\n"
            f"Deleted {len(junk_uids)} junk emails.\n"
            f"Retained {len(kept_msgs)} emails.\n"
            f"Deleted messages log: messages_deleted.txt\n"
            f"Kept messages log: messages_kept.txt\n"
        )

        # Send notification with attachments
        self.msgraphapi.send_email(
            subject=f"Outlook Junk Filter - {str(date.today())}",
            body=report,
            recipients=[config.EMAIL_ID],
            attachments=["messages_deleted.txt", "messages_kept.txt"]
        )

        logger.info(f'sent report: {report}')

    def filter_junk_emails(self, emails):
        """
        Filter junk emails based on keywords and sender information.
        """
        junk_uids = []
        kept_msgs = []
        junk_domains = set()
        jkws = set(junk_keywords.junk_keywords)

        del_file = open("messages_deleted.txt", "w")
        kept_file = open("messages_kept.txt", "w")

        regex = re.compile('[^a-zA-Z0-9]')
        try:
            for email in tqdm.tqdm(emails, desc="Processing emails", bar_format='{percentage:3.0f}%|{bar:20}| {remaining}s left'):
                email_id = email.get("id")
                sender = email.get("from", {}).get("emailAddress", {}).get("address", "")
                subject = email.get("subject", "")

                if sender:
                    domain = sender.split("@")[-1]
                    domain_parts = domain.split(".")
                    if len(domain_parts) < 2:
                        junk_uids.append(email_id)
                        del_file.write(f"Invalid sender: {sender}\n")
                        continue

                    # Process sender name and filter junk based on keywords
                    from_name = email.get("from", {}).get("emailAddress", {}).get("name", "")
                    if from_name:
                        from_name = unidecode(from_name)
                        squashed_from = regex.sub('', from_name).lower()

                    if squashed_from:
                        # Check junk criteria
                        jkws_match = any(kw in squashed_from for kw in jkws)

                        persist_kw = None
                        if not jkws_match:
                            persist_kw = any(kw in squashed_from for kw in self.persist.configs.get('keywords',{}).keys())

                        persist_dsfx = None
                        if not persist_kw:
                            persist_dsfx = domain in self.persist.configs.get('domain_sfx',{}).keys()
                        persist_dkim = None
                        if not persist_dsfx:
                            persist_dkim = domain in self.persist.configs.get('domain_dkim',{}).keys()
                        if jkws_match or persist_kw or persist_dsfx or persist_dkim:
                            junk_uids.append(email_id)
                            junk_domains.add(domain)
                            del_file.write(f"Junk sender: {squashed_from}, Email: {sender}, {email.get('fp')}\n")
                            self.persist.update('keywords', squashed_from)
                            self.persist.update('domain_sfx', domain)
                            fp = email.get('fp', {})
                            self.persist.update('domain_dkim', fp.get('dkim'))
                            self.persist.update('ipaddrs', fp.get('ip'), {'domain': fp.get('dkim')})
                            continue

                    # If not junk, keep email
                    kept_msgs.append(email)
                    if squashed_from:
                        kept_file.write(f"{squashed_from}, From: {sender}, Subject: {subject}\n")

        except Exception as e:
            logger.error("An error occurred:", str(e))
            traceback.print_exc()
        finally:
            del_file.close()
            kept_file.close()

        self.persist.print()
        self.persist.save_all()
        return junk_uids, kept_msgs, junk_domains


def check_debug_logging():
    parser = argparse.ArgumentParser()
    parser.add_argument('--info', action='store_true', help='Enable info output')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--debug_all', action='store_true', help='Enable debug output')
    args = parser.parse_args()
    # 🔧 Configure logging format and root level
    # Global config to silence other modules

    if args.debug_all:
        logging_level_for_all = logging.DEBUG
    else:
        logging_level_for_all = logging.WARNING


    logging.basicConfig(
        format='[%(name)s] %(funcName)s(): %(message)s',
        level=logging_level_for_all
    )

    if not args.debug_all:
        logging_level = logging.WARNING
        if args.info:
            logging_level = logging.INFO
        if args.debug:
            logging_level = logging.DEBUG
        logging.getLogger("junkconfig").setLevel(logging_level)
        logging.getLogger("msgraphapi").setLevel(logging_level)
        logging.getLogger("persistence").setLevel(logging_level)


if __name__ == "__main__":
    check_debug_logging()

    ojf = OutlookJunkFilter()
    try:
        # Retrieve and filter emails
        emails = ojf.get_junk_emails()
        junk_uids, kept_msgs, junk_domains = ojf.filter_junk_emails(emails)

        # Delete junk emails
        ojf.delete_emails([junk_uids[0]])

        ojf.send_report(junk_uids, kept_msgs)

    except Exception as e:
        logger.error("An error occurred:", str(e))
        traceback.print_exc()
