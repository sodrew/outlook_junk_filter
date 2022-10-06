# outlook_junk_filter

## Is this your Use Case?
You have a Outlook/Hotmail account and you want to delete true junk out of your "junk" folder

## Context for creation
Outlook/Hotmail doesn't provide a very good way of deleting junk mail in the junk mail.  The rules don't apply to the sender name, but it's pretty easy to identify junk by the sender name.  By sender name I mean the John Doe in "John Doe" <jdoe@domain.com>

## How to use this:
1. Install python3 and pip (google this)
1. Enable an app password for your outlook/hotmail: https://support.microsoft.com/en-us/account-billing/manage-app-passwords-for-two-step-verification-d6dc8c6d-4bf7-4851-ad95-6d07799387e9
    1. Login to hotmail
    1. Go to the top right and click your picture
    1. Click "My Microsoft Account"
    1. Click "Security" on the top banner
    1. Click "Advanced security options" (on this page, make sure that Two Step verification is enabled, if not, enable it)
    1. Click "Create New App password" (if you can't find this on the page, enable two step verification)
1. Edit the config file with your email and app password
1. Update dependencies in pip (really just tqdm):
    pip install -r requirements.txt --upgrade
1. Run the script!  You could set it to be a cron job or just run it on demand.
    python3 outlook_junk_filter.py

