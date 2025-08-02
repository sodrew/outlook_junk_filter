import os
import base64
import requests
from pprint import pprint, pformat
from msal import PublicClientApplication, SerializableTokenCache
import logging
logger = logging.getLogger("msgraphapi")

import config

# proper config:
#  API Permission: Mail.ReadWrite, Mail.Send (application not delegated)
#  Authentication: allow public client flows (to enable device_codes for auth)

class MSGraphAPI:
    def __init__(self):
        self.access_token = None
        self.access_token_cache = 'msal_token_cache.json'

    def authenticate(self):
        AUTHORITY = f"https://login.microsoftonline.com/common"
        SCOPES = ["Mail.ReadWrite", "Mail.Send"]

        # === Set up token cache ===
        cache = SerializableTokenCache()

        if os.path.exists(self.access_token_cache):
            cache.deserialize(open(self.access_token_cache, "r").read())

        app = PublicClientApplication(
            config.CLIENT_ID,
            authority=AUTHORITY,
            token_cache=cache
        )

        # === Try to use cached token ===
        accounts = app.get_accounts()
        #accounts = None
        if accounts:
            result = app.acquire_token_silent(SCOPES, account=accounts[0])
        else:
            result = None

        # === If no valid token, do interactive login ===
        if not result:
            # result = app.acquire_token_interactive(scopes=SCOPES)
            flow = app.initiate_device_flow(scopes=SCOPES)
            print(flow)
            if "user_code" not in flow:
                raise Exception("Failed to initiate device code flow")

            print(f"\n🔐 To sign in, go to {flow['verification_uri']} and enter the code: {flow['user_code']}\n")

            result = app.acquire_token_by_device_flow(flow)

        # === Save updated cache ===
        if cache.has_state_changed:
            with open(self.access_token_cache, "w") as f:
                f.write(cache.serialize())

        if 'access_token' in result:
            self.access_token = result['access_token']
            logger.info("Authentication successful.")
        else:
            logger.warm("Authentication failed:", result)
            raise Exception("Unable to authenticate.")


    def get_api(self, api_url):
        if self.access_token:
            headers = {
                'Authorization': f"Bearer {self.access_token}",
                'Content-Type': 'application/json'
            }

            # Only prepend base if relative path is used
            if api_url.startswith("http"):
                url = api_url
            else:
                url = f"https://graph.microsoft.com/v1.0/me/{api_url}"

            logger.info(f"GET: {url}")
            response = requests.get(url, headers=headers)
            try:
                data = response.json()
            except Exception:
                logger.error("Response not JSON:")
                logger.error(response.text)
                raise
            logger.debug(pformat(data))
            return data
        else:
            logger.warn('error: not authenticated')
            return {}

    def post_api(self, api_url, payload):
        headers = {
            'Authorization': f"Bearer {self.access_token}",
            'Content-Type': 'application/json'
        }
        base_url = 'https://graph.microsoft.com/v1.0/me/'
        url = base_url + api_url
        logger.debug(f"POST {url}")
        response = requests.post(url, headers=headers, json=payload)
        data = None
        logger.debug(f'Response code: {response.status_code}')
        if 'application/json' in response.headers.get('Content-Type', ''):
            try:
                data = response.json()
                logger.debug(f"Response data: {pformat(data)}")
            except ValueError:
                logger.error("❌ Response body is not valid JSON.")
        return data

    def delete_api(self, api_url):
        headers = {
            'Authorization': f"Bearer {self.access_token}"
        }
        base_url = 'https://graph.microsoft.com/v1.0/me/'
        url = base_url + api_url
        logger.debug(f"DELETE {url}")
        response = requests.delete(url, headers=headers)
        if response.status_code != 204:
            logger.warning(f"Failed to delete: {response.status_code}")

    def batch_delete_msgs(self, message_ids):
        batch_url = "https://graph.microsoft.com/v1.0/$batch"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        batch_requests = []
        for idx, message_id in enumerate(message_ids):
            batch_requests.append({
                "id": str(idx),
                "method": "DELETE",
                "url": f"/me/messages/{message_id}"
            })

        logger.debug(pformat(batch_requests))

        # Split into batches of 20 (Graph API limit)
        for i in range(0, len(batch_requests), 20):
            payload = {
                "requests": batch_requests[i:i + 20]
            }

            response = requests.post(batch_url, headers=headers, json=payload)
            if response.status_code == 200:
                logger.info(f"✅ Deleted batch {i // 20 + 1}")
            else:
                logger.error(f"❌ Batch {i // 20 + 1} failed with status {response.status_code}")
                logger.debug("Response JSON: %s", response.json())

    def send_email(self, subject, body, recipients, attachments=None):
        """
        Send an email using Microsoft Graph API.
        """
        # Prepare file attachments
        file_attachments = []
        for file_path in attachments or []:
            with open(file_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
            file_attachments.append({
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": os.path.basename(file_path),
                    "contentBytes": encoded
                })

        message = {
            "message": {
                "subject": subject,
                "body": {"contentType": "Text", "content": body},
                "toRecipients": [{"emailAddress": {"address": recipient}} for recipient in recipients],
                "attachments": file_attachments,
            },
            # "saveToSentItems": "false"
        }

        self.post_api('sendMail', message)

if __name__ == "__main__":
    msgraphapi = MSGraphAPI()
    msgraphapi.authenticate()
    data = msgraphapi.get_api('mailFolders/JunkEmail/messages?$top=1')
    pprint(data)
