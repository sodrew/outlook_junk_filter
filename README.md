# outlook_junk_filter

## Is this your Use Case?
You have a Outlook/Hotmail account and you want to delete true junk out of your "junk" folder

## Context for creation
Outlook/Hotmail doesn't provide a very good way of deleting junk mail in the junk mail.  The rules don't apply to the sender name, but it's pretty easy to identify junk by the sender name.  By sender name I mean the John Doe in "John Doe" <jdoe@domain.com>

## How to use this:
1. Enable an app password for your outlook/hotmail: https://support.microsoft.com/en-us/account-billing/manage-app-passwords-for-two-step-verification-d6dc8c6d-4bf7-4851-ad95-6d07799387e9
2. Edit the config file with your email and app password
3. Run the script!  You could set it to be a cron job or just run it on demand.

## Caveats:
This is super basic, and would be better re-written to look at every email in the junk folder and do check different permutations and regexes of a more concise junk_keyword list.  But this works well enough and I need to spend itme on other things...
