import json
import os
from datetime import date
import logging
from base64 import b64decode, b64encode
from pprint import pformat

logger = logging.getLogger("persistence")

class Persistence:
    def __init__(self, msapi, draft_subject="[JUNKCONFIG STATE]"):
        self.msapi = msapi
        self.draft_subject = draft_subject
        self.draft_id = None
        self.configs = {}

        self._load_or_create_draft()

    def _load_or_create_draft(self):
        """Search for an existing draft by subject, or create a new one."""
        logger.debug("Searching for existing config draft...")
        drafts = self.msapi.get_api("mailFolders/drafts/messages?$top=10")
        for msg in drafts.get("value", []):
            if msg.get("subject") == self.draft_subject:
                self.draft_id = msg["id"]
                logger.debug(f"Found draft: {self.draft_id}")
                self._load_attachments()
                return

        # Not found — create a new draft
        logger.debug("Creating new draft for config state.")
        body = {
            "subject": self.draft_subject,
            "body": {
                "contentType": "Text",
                "content": "Persistent junk filter config"
            },
            "toRecipients": []
        }

        created = self.msapi.post_api("mailFolders/drafts/messages", body)
        self.draft_id = created["id"]
        logger.debug(f"Created new draft: {self.draft_id}")

    def _load_attachments(self):
        """Load all JSON config attachments from the draft."""
        url = f"mailFolders/drafts/messages/{self.draft_id}/attachments"
        attachments = self.msapi.get_api(url)

        for a in attachments.get("value", []):
            name = a.get("name", "")
            if name.endswith(".json"):
                content = b64decode(a.get("contentBytes", "")).decode("utf-8")
                try:
                    self.configs[name[:-5]] = json.loads(content)
                    logger.debug(f"Loaded attachment: {name}")
                except Exception as e:
                    logger.warning(f"Could not decode {name}: {e}")

    def update(self, config_name, value, extra={}):
        if not value:
            logger.debug(f"Skipped updating {config_name} because null")
            return
        """Update a single config value (count + last_seen)."""
        today = str(date.today())
        cfg = self.configs.setdefault(config_name, {})

        if value in cfg:
            cfg[value]["count"] += 1
        else:
            cfg[value] = {'count': 1}

        cfg[value]["last_seen"] = today
        for k, v in extra.items():
            cfg[value][k] = v

        logger.debug(f"Updated {config_name}: {value} -> {cfg[value]}")

    def print(self):
        for name, data in self.configs.items():
            logger.info(f'name: {name}, count: {len(data)}')
            logger.debug(pformat(data))

    def format_json(self, data):
        lines = ["{"]
        keys = sorted(data.keys())
        for i, k in enumerate(keys):
            key = json.dumps(k)
            val = json.dumps(data[k], separators=(",", ": "))
            comma = "," if i < len(keys) - 1 else ""
            lines.append(f"  {key}: {val}{comma}")
        lines.append("}")
        return "\n".join(lines)

    def save_all(self):
        """Persist all config states back to draft as attachments."""
        if not self.draft_id:
            raise RuntimeError("Draft not initialized")

        # Delete old attachments
        attach_url = f"mailFolders/drafts/messages/{self.draft_id}/attachments"
        attachments = self.msapi.get_api(attach_url)
        for a in attachments.get("value", []):
            self.msapi.delete_api(f"{attach_url}/{a['id']}")
            logger.debug(f"Deleted old attachment: {a['name']}")

        # Upload new attachments
        for name, data in self.configs.items():
            file_content = self.format_json(data).encode("utf-8")
            attachment = {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": f"{name}.json",
                "contentBytes": b64encode(file_content).decode("utf-8")
            }
            self.msapi.post_api(attach_url, attachment)
            logger.debug(f"Attached new {name}.json to draft")

    def get_all(self, config_name):
        return self.configs.get(config_name, {})

if __name__ == "__main__":
    logging.basicConfig(
        format='[%(name)s] %(funcName)s(): %(message)s',
        level=logging.WARNING
    )
    logging.getLogger("persistence").setLevel(logging.DEBUG)

    from msgraphapi import MSGraphAPI

    msapi = MSGraphAPI()
    msapi.authenticate()

    p = Persistence(msapi)

    p.update("keywords", "cheapdealz")
    p.update("domain_sfx", "cheapdealz.com")
    p.update("domain_dkim", "cheapdealz.com")
    p.update("ipaddrs", "123.452.234.234")
    p.save_all()
