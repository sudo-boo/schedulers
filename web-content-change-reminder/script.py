import os
import json
import pytz
import requests
import datetime
import smtplib
import difflib
import html
from bs4 import BeautifulSoup
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
load_dotenv()

SENDER_EMAIL = str(os.getenv("SENDER_EMAIL"))
if not SENDER_EMAIL:
    raise ValueError("SENDER_EMAIL not found in .env file.")

SENDER_PASSWORD = str(os.getenv("SENDER_PASSWORD"))
if not SENDER_PASSWORD:
    raise ValueError("SENDER_PASSWORD not found in .env file.")

if SENDER_EMAIL and SENDER_PASSWORD:
    print(GREEN + "Environment variables loaded successfully." + COLOR_OFF)
else:
    raise ValueError("One or more environment variables are missing. Please check your .env file.")

# read user_configs.json file
try:
    with open("user_configs.json", "r") as f:
        config = json.load(f)
        user_emails = config.get("users", [])
        websites = config.get("websites", [])
        print(GREEN + "user_configs.json loaded successfully." + COLOR_OFF)
        
except Exception as e:
    raise Exception(f"An error occurred while reading user_configs.json: {e}")
        
RECEIVER_EMAILS = [(user["email"], user["name"]) for user in user_emails]

# Include the optional selector in the tuple (defaults to None if missing)
WEBSITES = [(site["name"], site["url"], site.get("selector")) for site in websites]

def current_time_str():
    return datetime.datetime.now(IST).strftime("%H:%M:%S")

def extract_target_content(full_html, selector, site_name):
    """Extracts a specific part of the HTML based on a CSS selector."""
    if not selector:
        return full_html # If no selector provided, check the whole page
        
    soup = BeautifulSoup(full_html, 'html.parser')
    element = soup.select_one(selector)
    
    if element:
        # .prettify() normalizes the HTML making the diff much cleaner to read
        return element.prettify()
    else:
        print(YELLOW + f"⚠️ Warning: Selector '{selector}' not found on {site_name}. Defaulting to full HTML check." + COLOR_OFF)
        return full_html

def check_and_archive_changes():
    changes = []
    now_str = datetime.datetime.now(IST).strftime("%Y-%m-%d_%H-%M-%S")
    
    for name, url, selector in WEBSITES:
        try:
            site_dir = os.path.join("archives", name)
            os.makedirs(site_dir, exist_ok=True)
            latest_path = os.path.join(site_dir, "latest.html")
            
            # Fetch content
            response = requests.get(url)
            response.raise_for_status()
            current_full_content = response.text
            
            # First-time setup
            if not os.path.exists(latest_path):
                with open(latest_path, "w", encoding="utf-8") as f:
                    f.write(current_full_content)
                with open(os.path.join(site_dir, f"{now_str}.html"), "w", encoding="utf-8") as f:
                    f.write(current_full_content)
                print(YELLOW + f"No previous content found for {name}. Saved initial version." + COLOR_OFF)
                continue
            
            # Read old content
            with open(latest_path, "r", encoding="utf-8") as f:
                old_full_content = f.read()
            
            # Extract target areas for comparison
            current_target = extract_target_content(current_full_content, selector, name)
            old_target = extract_target_content(old_full_content, selector, name)
            
            # Compare and generate diff
            if current_target != old_target:
                diff_generator = difflib.unified_diff(
                    old_target.splitlines(),
                    current_target.splitlines(),
                    fromfile='Previous',
                    tofile='Current',
                    n=3,
                    lineterm=''
                )
                diff_list = list(diff_generator)
                
                changes.append((name, url, diff_list))
                
                # Update latest.html and create a new archived version with the FULL HTML
                with open(latest_path, "w", encoding="utf-8") as f:
                    f.write(current_full_content)
                with open(os.path.join(site_dir, f"{now_str}.html"), "w", encoding="utf-8") as f:
                    f.write(current_full_content)
                    
                print(GREEN + f"✅ Change detected on {name}! Archived full HTML as {now_str}.html" + COLOR_OFF)
            else:
                print(GREEN + f"No change detected on {name}." + COLOR_OFF)
                
        except Exception as e:
            print(RED + f"Failed to check/save content for {name}: {e}" + COLOR_OFF)
            
    return changes

def send_email(changes):
    if not changes:
        return

    subject = "🚨 Website Change Detected!"

    # === PLAIN TEXT VERSION ===
    plain_body = "Hey!\n\nChanges detected on monitored websites:\n\n"
    for name, url, diff in changes:
        plain_body += f"🔹 {name}\nURL: {url}\nChanges:\n"
        plain_body += "\n".join(diff[:50])
        if len(diff) > 50:
            plain_body += "\n... (diff truncated)"
        plain_body += "\n" + "-"*50 + "\n\n"
    plain_body += "Stay updated 🚀\n— Web Monitor Bot"

    # === HTML VERSION ===
    html_body = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; }
            .container { padding: 10px; }
            .card {
                border: 1px solid #ddd; border-radius: 8px;
                margin-bottom: 20px; padding: 15px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            .title { font-size: 18px; font-weight: bold; color: #007acc; }
            .url { font-size: 13px; margin-bottom: 10px; }
            .diff {
                background: #2b2b2b; color: #f8f8f2;
                padding: 10px; border-radius: 5px;
                font-family: monospace; font-size: 12px;
                white-space: pre-wrap; overflow-x: auto;
            }
            .added { color: #50fa7b; background-color: rgba(80, 250, 123, 0.2); padding: 2px 0; }
            .removed { color: #ff5555; background-color: rgba(255, 85, 85, 0.2); text-decoration: line-through; padding: 2px 0; }
            .context { color: #bbbbbb; padding: 2px 0; }
            .chunk-header { color: #8be9fd; font-weight: bold; margin-top: 10px; border-bottom: 1px solid #444; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🚨 Website Changes Detected</h2>
            <p>Here’s what changed:</p>
    """

    for name, url, diff_list in changes:
        formatted_diff = ""
        for line in diff_list:
            safe_line = html.escape(line)
            if safe_line.startswith('+') and not safe_line.startswith('+++'):
                formatted_diff += f"<div class='added'>{safe_line}</div>"
            elif safe_line.startswith('-') and not safe_line.startswith('---'):
                formatted_diff += f"<div class='removed'>{safe_line}</div>"
            elif safe_line.startswith('@@'):
                formatted_diff += f"<div class='chunk-header'>{safe_line}</div>"
            elif safe_line.startswith('+++') or safe_line.startswith('---'):
                continue 
            else:
                formatted_diff += f"<div class='context'>{safe_line}</div>"

        html_body += f"""
        <div class="card">
            <div class="title">{name}</div>
            <div class="url"><a href="{url}">{url}</a></div>
            <div class="diff">{formatted_diff}</div>
        </div>
        """

    html_body += """
            <p>Stay updated 🚀<br><br>— Web Monitor Bot</p>
        </div>
    </body>
    </html>
    """

    # === EMAIL SETUP ===
    msg = MIMEMultipart("alternative")
    msg['From'] = SENDER_EMAIL
    msg['To'] = ", ".join([email for email, _ in RECEIVER_EMAILS])
    msg['Subject'] = subject

    msg.attach(MIMEText(plain_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(
            SENDER_EMAIL,
            [email for email, _ in RECEIVER_EMAILS],
            msg.as_string()
        )
        server.quit()
        print(GREEN + "✅ Email sent successfully!" + COLOR_OFF)
    except Exception as e:
        print(RED + f"Failed to send email: {e}" + COLOR_OFF)

def main():
    print()
    print(YELLOW + f"Running script at {current_time_str()}..." + COLOR_OFF)
    
    changes = check_and_archive_changes()
    
    if changes:
        print()
        for name, _, _ in changes:
            print(YELLOW + f"- {name}" + COLOR_OFF)
        print()
        send_email(changes)

    print(GREEN + "Script completed." + COLOR_OFF)

if __name__ == '__main__':
    main()