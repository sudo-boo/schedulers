# CP-Reminder

A reminder service for competitive programming (CP) contests.

## Setup Instructions

To get started, follow the instructions below to set up the CP-Reminder project.

### 1. Fork the Repository

First, fork this repository to your own GitHub account.

1. Click the **Fork** button in the top-right corner of the page to create a copy of the repository in your GitHub account.

### 2. Configure Your Preferences

Finally, to receive contest reminders through email, change the following fields in user_configs.json

1. Add your email address and other parameter changes in the file like this:

    ```json
    {
        "_comments": {
            "users": "List of users to fetch emails for",
            "params": "Parameters to pass to the API"
        },
        "users": [
            {
                "name": "Email 1",
                "email": "trallalero-tralla@he.he"
            },
            {
                "name": "Email 2",
                "email": "chimpanzini-bananini@he.he"
            }
        ]
        "params": {
            "upcoming": "true",
            "start_time__during": "2 days",
            "format": "json",
            "limit": 100
        },
    }
    ```

2. By default, the workflow runs 2 times a day (07:30 UTC (13:00 IST) and 13:30 UTC (19:00 IST)). You can change this in the `.github/workflows/main.yml` under `cron` section.

### 3. Create Your API Key on Codeforces List (Clist)

You'll need to create an API key from Clist in order to fetch contest data.

1. Go to [Clist API](https://clist.by/api/v4/doc/).
2. Sign up or log in if you don't already have an account.
3. Create an API key from your account settings.
4. Store your API key securely as you will need it for the next step.

**Read how to do it here**: [Clist API Docs](https://clist.by/docs/#authentication)

### 4. Create an App Password for Email Notifications

For sending email reminders, you’ll need to create an app-specific password for the email service you want to use (e.g., Gmail).

### Gmail (or other email services)

1. Go to your [Google Account](https://myaccount.google.com/).
2. Under **Security**, scroll to **App passwords**.
3. Select the app and device you want to generate the password for.
4. Save the generated password.

**Read how to do it here**: [Google App Passwords](https://support.google.com/accounts/answer/185833?hl=en)

### 5. Add Secrets to GitHub

Once you’ve got your Clist API Key and email app password, you need to add them to your GitHub secrets.

1. Go to your forked repository.
2. Navigate to **Settings** > **Secrets and variables** > **Actions**.
3. Add the following secrets:
   - `API_KEY`: Your Clist API key.
   - `SENDER_EMAIL`: Your sender email.
   - `SENDER_PASSWORD`: Your email app password.

**Read how to do it here**: [GitHub Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)

### And you're all set!!

### Happy Coding!!
