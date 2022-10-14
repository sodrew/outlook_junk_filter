import re
import email.header
import imaplib
import tqdm

import config
import junk_keywords


class OutlookJunkFilter():
    def __init__(self):
        self.imap = None

    def login(self, username, password):
        self.username = username
        self.password = password
        try:
            self.imap = imaplib.IMAP4_SSL(config.server,
                                          config.port)
            # self.imap.starttls()
            r, d = self.imap.login(username, password)
            assert r == 'OK', 'login failed: %s' % str(r)
            print("\tSigned in as %s" % self.username)
        except Exception as err:
            print("\tSign in error: %s" % str(err))
            assert False, 'login failed'

    def logout(self):
        self.imap.close()
        self.imap.logout()

    def delete_junk(self, msgs):
        if(len(msgs) > 0):
            print(f'\tExecuting delete')
            self.imap.uid('STORE',
                          ','.join(msgs),
                          '+FLAGS', '\\Deleted')
            print(f'\t{len(msgs)} msgs were deleted')
        else:
            print(f'\tNo msgs were deleted')

    def parse(self, uid, from_str, subj):
        pattern = r'([^<]*)<([^@]*)@([^>]*)>'
        matches = re.search(pattern, from_str[6:])
        if(matches):
            return {'uid': uid,
                    'from': from_str[6:].replace('"', ''),
                    'f_name': matches.group(1).replace('"', ''),
                    'f_user': matches.group(2),
                    'f_domain': matches.group(3),
                    'subj': subj[9:]}
        else:
            pattern = r'([^@]*)@([^$]*)'
            matches = re.search(pattern, from_str[6:])
            if(matches):
                return {'uid': uid,
                        'from': from_str[6:],
                        'f_user': matches.group(1),
                        'f_domain': matches.group(2),
                        'subj': subj[9:]}
            else:
                return {'uid': uid,
                        'from': from_str[6:],
                        'subj': subj[9:]}

    def decode_mime_words(self, s):
        words=[]
        decoded = False
        for word, encoding in email.header.decode_header(s):
            if(encoding):
                decoded = True
            if isinstance(word, bytes):
                word = word.decode(encoding or 'utf8')
            words.append(word)
        return (''.join(words), decoded)

    def ireplace(self, old, repl, text):
        return re.sub('(?i)'+re.escape(old), lambda m: repl, text)

    def iterate_msgs(self):
        kept_msgs = []
        junk_uids = []
        junk_domains = set()
        jkws = set(junk_keywords.junk_keywords)
        pattern = r'([^@]*)@([^$]*)'
        matches = re.search(pattern, self.username)
        if(matches):
            jkws.add(matches.group(1)),

        self.imap.select('Junk')

        r, d = self.imap.uid('SEARCH', 'ALL')
        if(not d[0].decode()):
            print('\tExiting, no emails found')
            return junk_uids

        uids = d[0].decode().split(' ')

        if(len(uids) < 1):
            print('\tExiting, no emails found')
            return junk_uids

        print(f'\t{len(uids)} msgs to process in "Junk Email" folder')

        del_file = open("messages_deleted.txt", "w")
        kept_file = open("messages_kept.txt", "w")

        regex = re.compile('[^a-zA-Z0-9]')
        try:
            with tqdm.tqdm(total=len(uids), bar_format='\t{percentage:3.0f}%[{bar:20}] {remaining}s left') as pbar:
                for uid in uids:
                    resp, data = self.imap.uid('FETCH',
                                           str(uid),
                                           '(BODY.PEEK[HEADER.FIELDS (From Subject)] RFC822.SIZE)')
                    raw_header = data[0][1].decode()
                    (decoded_header, decoded) = self.decode_mime_words(raw_header)
                    if(decoded):
                        if(decoded_header[0:4].lower() == 'from'):
                            decoded_header = self.ireplace('Subject', '\r\nSubject', decoded_header)
                        else:
                            decoded_header = self.ireplace('From', '\r\nFrom', decoded_header)

                    from_subject = decoded_header.split('\r\n')

                    if(from_subject[0][0:4] == 'From'):
                        parsed = self.parse(uid, from_subject[0], from_subject[1])
                    else:
                        parsed = self.parse(uid, from_subject[1], from_subject[0])
                    if('f_domain' not in parsed):
                        # if we can't find an email domain, this is junk
                        junk_uids.append(parsed['uid'])
                        del_file.write(f"raw={parsed['from']}\n")
                    else:
                        domain_parts = parsed['f_domain'].split('.')
                        if(len(domain_parts) == 0):
                            # invalid domain, this is more junk
                            junk_uids.append(parsed['uid'])
                            junk_domains.add(parsed['f_domain'])
                            del_file.write(f"raw={parsed['from']}\n")
                        elif('f_name' in parsed):
                            # if we have a from name, check it for typical junk
                            from unidecode import unidecode
                            # first, convert any unicode to ascii
                            f_name = unidecode( parsed['f_name'])

                            # second, we strip all non a-Z characters
                            f_name = regex.sub('', f_name).lower()

                            # third, ensure the from and user doesn't match the domain (we strip the last participle..mostly the .com).  (e.g., warby parkers shouldn't be deleted if the domain is legit
                            if(not any(dp.lower() in f_name for dp in domain_parts[:-1]) and
                               parsed['f_user'].lower() not in f_name and
                               any(keyword in f_name for keyword in jkws)):
                                junk_uids.append(parsed['uid']);
                                junk_domains.add(parsed['f_domain'])
                                del_file.write(f"sender={parsed['f_name']} email={parsed['f_user']}@{parsed['f_domain']} debug={f_name}\n")
                            else:
                                kept_msgs.append(parsed)
                                kept_file.write(f"sender={parsed['f_name']} email={parsed['f_user']}@{parsed['f_domain']} debug={f_name}\n")
                        else:
                            kept_msgs.append(parsed)
                            kept_file.write(f"email={parsed['f_user']}@{parsed['f_domain']} debug={f_name}\n")

                    pbar.update(1)
            junk_pct = len(junk_uids)/len(uids) * 100
            count = 0
            for msg in kept_msgs:
                if(msg['f_domain'] in junk_domains):
                    junk_uids.append(msg['uid'])
                    del_file.write(f"sender={msg['f_name']} email={msg['f_user']}@{msg['f_domain']} debug=<junk_domain>\n")
                    count += 1
            if(count > 0):
                print(f"\t{len(junk_uids)} junk messages found based on keywords; {count} by common domain")
            else:
                print(f"\t{len(junk_uids)} ({junk_pct:.1f}%) were junk msgs")
            print('\t\tdeleted msgs can be found in: messages_deleted.txt')
            print('\t\tretained msgs can be found in: messages_kept.txt')
        finally:
            kept_file.close()
            del_file.close()

        return junk_uids


def main():
    mail = OutlookJunkFilter()
    try:
        mail.login(config.user, config.pwd)
        junk_uids = mail.iterate_msgs()
        mail.delete_junk(junk_uids)
    finally:
        mail.logout()


if __name__ == "__main__":
    main()
