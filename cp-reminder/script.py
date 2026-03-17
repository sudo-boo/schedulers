import os
import json
import pytz
import requests
import datetime
import smtplib
from dateutil import parser
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# === COLORS FOR TERMINAL ===
COLOR_OFF = '\033[0m'
YELLOW = '\033[0;33m'
GREEN = '\033[0;32m'
RED = '\033[0;31m'

IST = pytz.timezone('Asia/Kolkata')

# === CONFIGURATION ===

# read from .env file
load_dotenv()
API_KEY = str(os.getenv("API_KEY"))
if not API_KEY:
    raise ValueError("API_KEY not found in .env file.")

SENDER_EMAIL = str(os.getenv("SENDER_EMAIL"))
if not SENDER_EMAIL:
    raise ValueError("SENDER_EMAIL not found in .env file.")

SENDER_PASSWORD = str(os.getenv("SENDER_PASSWORD"))
if not SENDER_PASSWORD:
    raise ValueError("SENDER_PASSWORD not found in .env file.")

if API_KEY and SENDER_EMAIL and SENDER_PASSWORD:
    print(GREEN + "Environment variables loaded successfully." + COLOR_OFF)
else:
    raise ValueError("One or more environment variables are missing. Please check your .env file.")

# read user_emails.json file
try:
    with open("user_configs.json", "r") as f:
        config = json.load(f)
        user_emails = config.get("users", {})
        PARAMS = config.get("params", {})
        print(GREEN + "user_emails.json loaded successfully." + COLOR_OFF)
        
except FileNotFoundError:
    raise FileNotFoundError("user_emails.json file not found. Please create it with user emails.")
except json.JSONDecodeError:
    raise ValueError("user_emails.json file is not a valid JSON. Please check the format.")
except Exception as e:
    raise Exception(f"An error occurred while reading user_emails.json: {e}")
        
        
RECEIVER_EMAILS = [
    (user["email"], user["name"]) for user in user_emails
]


TARGET_RESOURCES = {"codeforces", "leetcode", "codechef"}

HEADERS = {
    'Authorization': f'ApiKey {API_KEY}'
}

URL = "https://clist.by/api/v4/contest/"


def current_time_str():
    return datetime.datetime.now().strftime("%H:%M:%S")


def fetch_contests():
    response = requests.get(URL, headers=HEADERS, params=PARAMS)
    if response.status_code != 200:
        print(RED + f"API request failed: {response.status_code}" + COLOR_OFF)
        return []

    data = response.json()
    contests = data.get("objects", [])
    print(GREEN + f"Fetched {len(contests)} contests from API." + COLOR_OFF)

    now = datetime.datetime.now(datetime.timezone.utc)

    filtered = []
    for contest in contests:
        try:
            start_time = parser.isoparse(contest.get("start"))
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=datetime.timezone.utc)
            if start_time > now and any(site in contest.get('resource', '').lower() for site in TARGET_RESOURCES):
                filtered.append(contest)
        except Exception as e:
            print(RED + f"Skipping contest due to parse error: {e}" + COLOR_OFF)

    print(GREEN + f"{len(filtered)} contests matched filters (resource + upcoming)." + COLOR_OFF)
    return filtered


def format_time_remaining(delta):
    """Format a timedelta as a human-readable string."""
    total_seconds = int(delta.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")

    return " ".join(parts)


def send_email(contests):
    if not contests:
        print(YELLOW + "No contests today to email." + COLOR_OFF)
        return

    subject = "📅 Upcoming Programming Contests"
    now_ist = datetime.datetime.now(IST)

    # Plain text fallback
    plain_body = "Hey!\n\nHere are the contests scheduled for today:\n\n"
    for contest in contests:
        start = parser.isoparse(contest["start"])
        if start.tzinfo is None:
            start = start.replace(tzinfo=datetime.timezone.utc)
        local_start = start.astimezone(IST)
        delta = local_start - now_ist
        time_remaining = format_time_remaining(delta)
        plain_body += (
            f"- {contest['event']} ({contest['resource']})\n"
            f"  Starts at: {local_start.strftime('%Y-%m-%d %H:%M %Z')} | Time Remaining: {time_remaining}\n"
            f"  Link: {contest['href']}\n\n"
        )
    plain_body += "Good luck!!\n\n— cp-reminder-bot 🤖"

    # HTML email body with styled table
    html_body = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; }
            table {
                border-collapse: collapse;
                width: 100%;
                margin-top: 10px;
            }
            th, td {
                border: 1px solid #dddddd;
                text-align: left;
                padding: 8px;
            }
            th {
                background-color: #007acc;
                color: white;
            }
            tr:nth-child(even) {
                background-color: #f9f9f9;
            }
            a {
                color: #007acc;
                text-decoration: none;
            }
        </style>
    </head>
    <body>
        <h2>Heyy!!</h2>
        <p>Here are the contests scheduled for today and tomorrow:</p>
        <table>
            <tr>
                <th>Platform</th>
                <th>Contest</th>
                <th>Start Time (IST)</th>
                <th>Time Remaining</th>
                <th>Link</th>
            </tr>
    """

    for contest in contests:
        start = parser.isoparse(contest["start"])
        if start.tzinfo is None:
            start = start.replace(tzinfo=datetime.timezone.utc)
        local_start = start.astimezone(IST)
        delta = local_start - now_ist
        time_remaining = format_time_remaining(delta)
        html_body += f"""
            <tr>
                <td>{contest['resource'].title()}</td>
                <td>{contest['event']}</td>
                <td>{local_start.strftime('%Y-%m-%d %H:%M')}</td>
                <td>{time_remaining}</td>
                <td><a href="{contest['href']}">View</a></td>
            </tr>
        """

    html_body += """
        </table>
        <p style="margin-top: 20px;">Good luck!!<br><br>— cp-reminder-bot 🤖</p>
    </body>
    </html>
    """

    # Construct email
    msg = MIMEMultipart("alternative")
    msg['From'] = SENDER_EMAIL
    msg['To'] = ", ".join([email for email, name in RECEIVER_EMAILS])
    msg['Subject'] = subject
    msg.attach(MIMEText(plain_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, [email for email, name in RECEIVER_EMAILS], msg.as_string())
        server.quit()
        print(GREEN + "✅ Email sent with upcoming contests." + COLOR_OFF)
    except Exception as e:
        print(RED + f"Failed to send email: {e}" + COLOR_OFF)


def main():
    print()
    print(YELLOW + f"Running script at {current_time_str()}..." + COLOR_OFF)
    contests = fetch_contests()
    if contests:
        print()
        for contest in contests:
            print(YELLOW + f"- {contest['event']} ({contest['resource']}) at {contest['start']}" + COLOR_OFF)
        print()
        send_email(contests)
    print(GREEN + "Script completed." + COLOR_OFF)


if __name__ == '__main__':
    main()
