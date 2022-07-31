import imaplib
import re

import config


class OutlookJunkFilter():
    def __init__(self, input_keywords):
        self.imap = None
        # we have to split the keywords because of the OR limitation
        self.keywordset = []
        keywords = []
        count = 0
        for keyword in input_keywords:
            keywords.append(keyword)
            count += 1
            if(keyword.find(' ') >= 0):
                keywords.append(keyword.replace(' ', ''))
                count += 1

            # looks like IMAP can only do a max of 9 or so operands for OR
            if(count >= 9):
                self.keywordset.append(keywords)
                keywords = []
                count = 0

        # get any remainder keywords
        if(count != 0):
            self.keywordset.append(keywords)

    def login(self, username, password):
        self.username = username
        self.password = password
        try:
            self.imap = imaplib.IMAP4_SSL(config.server,
                                          config.port)
            # self.imap.starttls()
            r, d = self.imap.login(username, password)
            assert r == 'OK', 'login failed: %s' % str(r)
            print("Signed in as %s" % self.username, d)
            return
        except Exception as err:
            print("Sign in error: %s" % str(err))
            assert False, 'login failed'

    def logout(self):
        self.imap.close()
        self.imap.logout()

    def parse(self, uid, from_str, subj):
        pattern = r'"([^"]*)" <([^@]*)@([^>]*)>'
        matches = re.search(pattern, from_str[6:])
        if(matches):
            return {'uid': uid,
                    'from': from_str[6:],
                    'f_name': matches.group(1),
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

    def list_msgs(self, criteria):
        msgs = []
        domains = {}
        if(not criteria):
            print('\tno criteria specified')
            return msgs, domains

        self.imap.select('Junk')
        r, d = self.imap.uid('SEARCH', criteria)
        if(not d[0].decode()):
            print('\tno emails found')
            return msgs, domains

        uids = d[0].decode().split(' ')

        if(len(uids) < 1):
            print('\tno uids returned')
            return msgs, domains


        resp, data = self.imap.uid('FETCH',
                                   ','.join(map(str, uids)),
                                   '(BODY.PEEK[HEADER.FIELDS (From Subject)] RFC822.SIZE)')
        iterator = iter(data)
        for rmsg in iterator:
            dmsg = rmsg[1].decode().split('\r\n')[:2]

            # uid is the next item in the array
            # so we use the iterator to manually advance
            rmsg = next(iterator)
            uid = rmsg.decode().split(' ')[4][:-1]
            if(dmsg[0][0:4] == 'From'):
                msg = self.parse(uid, dmsg[0], dmsg[1])
            else:
                msg = self.parse(uid, dmsg[1], dmsg[0])

            msgs.append(msg)
            if 'f_domain' in msg.keys():
                domain = msg['f_domain']
                if(domain not in domains.keys()):
                    domains[domain] = 0
                domains[domain] += 1
        return msgs, domains

    def build_or_criteria(self, items):
        if(len(items) == 0):
            return ''
        elif(len(items) == 1):
            return 'UNSEEN ' + items[0]
        else:
            count = 0
            ret = ''
            for item in items:
                if(count == 0):
                    pass
                elif(count == 1):
                    ret += f'OR {items[0]} {items[1]} '
                elif(count < 10):
                    ret = 'OR ' + ret + item + ' '
                else:
                    print(f'WARNING: OR limit reached: {item}')
                count += 1
            return 'UNSEEN ' + ret

    def delete_junk(self, msgs, domains):
        if(len(msgs) > 0):
            print(f'\tDeleting: {len(msgs)} msgs')
            self.imap.uid('STORE',
                          ','.join([msg['uid'] for msg in msgs]),
                          '+FLAGS', '\\Deleted')
        if(domains and len(domains) > 0):
            print('\tFinding msgs with same domains as junk msgs...')
            terms = []
            for domain, count in domains.items():
                if(count > 1):
                    terms.append(f'FROM "{domain}"')
            criteria = self.build_or_criteria(terms)
            if(criteria):
                msgs, domains = self.list_msgs(criteria)
                self.delete_junk(msgs, None)
        # self.imap.expunge()
        return len(msgs)

    def build_junk_criteria(self, keywords):
        ret = []
        for keyword in keywords:
            ret.append(f'FROM "{keyword}"')
        return self.build_or_criteria(ret)

    def find_junk(self, keywords):
        return self.list_msgs(self.build_junk_criteria(keywords))

    def process_junk(self):
        count = 1
        for keywords in self.keywordset:
            print(f'---Keywordset {count}: {keywords}---')
            msgs, domains = self.find_junk(keywords)
            if(len(msgs) > 0):
                print(f'\tfound: {len(msgs)} msgs for {len(domains)} domains')
                self.delete_junk(msgs, domains)
            count += 1


def main():
    mail = OutlookJunkFilter(config.junk_keywords)
    mail.login(config.user, config.pwd)
    mail.process_junk()
    mail.logout()


if __name__ == "__main__":
    main()
