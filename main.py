import base64
from email.mime.text import MIMEText
from email.utils import formataddr
from zoneinfo import ZoneInfo

from claudette import *
import os
os.environ['ANTHROPIC_LOG'] = 'debug'

model = models[1]
print("using model", model)


import functools

def debug_print(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        print(f"TOOL DEBUG: {func.__name__}() returned {result}")
        return result
    return wrapper

import json

def load_secrets(secrets_file: str = 'secrets.json') -> dict:
  try:
    with open(secrets_file, 'r') as f:
      secrets = json.load(f)
    return secrets
  except Exception as e:
    print(f"Failed to load secrets: {str(e)}")
    return {}

# Load secrets into a global variable
SECRETS = load_secrets()
os.environ["ANTHROPIC_API_KEY"] = SECRETS['ANTHROPIC_API_KEY']

import requests
import json

def http_request(
  url: str,  # The URL to send the request to
  method: str = 'GET',  # The HTTP method to use (GET, POST, PUT, DELETE, etc.)
  timeout: int = 30  # Timeout for the request in seconds
) -> str:  # Returns the Response object from the requests library
  """
  Performs an HTTP request to the specified URL using the given method and parameters.
  """
  print("fetching", url)
  try:
    response = requests.request(
      method=method.upper(),
      url=url,
      timeout=timeout
    )
    response.raise_for_status()
    return response.text
  except requests.RequestException as e:
    print(f"HTTP request failed: {str(e)}")
    raise

@debug_print
def notify_owner(
  subject: str,  # The subject of the notification email
  body: str      # The body content of the notification email
) -> bool:  # Returns True if email was sent successfully, False otherwise
  """
  Sends an email to the owner with the provided subject and body.
  """

  payload = {
    "text": body,
    "subject": subject
  }

  json_payload = json.dumps(payload)
  headers = {
    "Content-Type": "application/json"
  }
  try:
    response = requests.post(SECRETS['EMAIL_API_URL'], data=json_payload, headers=headers)

    if response.status_code == 200:
      print("Email sent successfully!")
      print("Response:", response.json())
    else:
      print(f"Failed to send email. Status code: {response.status_code}")
      print("Response:", response.text)

  except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")


from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
import os
import sys
from datetime import datetime

def can_launch_browser():
  if sys.platform.startswith('linux'):
    return 'DISPLAY' in os.environ or 'WAYLAND_DISPLAY' in os.environ
  elif sys.platform == 'darwin':
    return True  # macOS should always be able to launch a browser
  elif sys.platform == 'win32':
    return True  # Windows should always be able to launch a browser
  return False

def get_credentials(token_file: str, scopes: list):
  creds = None
  if os.path.exists(token_file):
    creds = Credentials.from_authorized_user_file(token_file, scopes)
  
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      try:
        creds.refresh(Request())
      except RefreshError:
        creds = None
    
    if not creds:
      if can_launch_browser():
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', scopes)
        creds = flow.run_local_server(port=0)
      else:
        raise EnvironmentError("Cannot perform interactive authentication. "
                               "Please run this script on a machine with a display first "
                               f"to generate the {token_file} file. Then copy the file to this headless environment.")
    
    # Save the credentials for the next run
    with open(token_file, 'w') as token:
      token.write(creds.to_json())
  
  return creds

CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
  CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']
  creds = get_credentials('token_calendar.json', CALENDAR_SCOPES)
  return build('calendar', 'v3', credentials=creds)

@debug_print
def check_calendar_availability(
  start_time: str,  # ISO format datetime string eg: 2024-06-23T14:00:00
  end_time: str,    # ISO format datetime string
  timezone: str # timezone
) -> str:  # Returns a string describing availability
  """
  Checks Google Calendar for availability within the specified time range.
  """
  print(f"Checking owner's calendar between {start_time} and {end_time} in {timezone}")
  service = get_calendar_service()
  
  # Convert string times to datetime objects with timezone
  start = datetime.fromisoformat(start_time).replace(tzinfo=ZoneInfo(timezone))
  end = datetime.fromisoformat(end_time).replace(tzinfo=ZoneInfo(timezone))
  
  # Call the Calendar API
  events_result = service.events().list(
    calendarId='primary',
    timeMin=start.isoformat(),
    timeMax=end.isoformat(),
    singleEvents=True,
    orderBy='startTime'
  ).execute()
  events = events_result.get('items', [])

  if not events:
    return f"User is available from {start_time} to {end_time} ({timezone})."
  else:
    busy_times = []
    for event in events:
      if event.get('transparency'):
        continue
      start = event['start'].get('dateTime', event['start'].get('date'))
      end = event['end'].get('dateTime', event['end'].get('date'))
      busy_times.append(f"{start} to {end}")
    if len(busy_times) == 0:
      return f"User is available from {start_time} to {end_time} ({timezone})."
    return f"User has the following commitments between {start_time} and {end_time} ({timezone}):\n" + "\n".join(busy_times)

#print(check_calendar_availability('2024-06-23T14:00:00','2024-06-29T14:00:00', 'Asia/Shanghai'))

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

from email.mime.text import MIMEText
from email.utils import formataddr
import base64
import re

GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']  # Changed to allow marking emails as read

def get_gmail_service():
  GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
  creds = get_credentials('token_gmail.json', GMAIL_SCOPES)
  return build('gmail', 'v1', credentials=creds)

def get_unread_count() -> int:
  service = get_gmail_service()
  
  # Get the number of unread emails
  results = service.users().messages().list(userId='me', labelIds=['INBOX', 'UNREAD']).execute()
  unread_count = results.get('resultSizeEstimate', 0)
  return unread_count


import html2text
from email import message_from_bytes, header

@debug_print
def read_email() -> str:
    """
    Checks the most recent unread email in the assistant's inbox and retrieves the entire thread.
    """
    print("Reading assistant's inbox...")
    service = get_gmail_service()
    
    # Get the number of unread emails
    results = service.users().messages().list(userId='me', labelIds=['INBOX', 'UNREAD']).execute()
    unread_count = results.get('resultSizeEstimate', 0)

    # Get the most recent unread email
    messages = results.get('messages', [])

    if not messages:
        return f"Number of unread emails: 0\nNo new messages."
    else:
        # Get the thread ID of the most recent unread email
        message = service.users().messages().get(userId='me', id=messages[0]['id'], format='raw').execute()
        thread_id = message['threadId']
        
        # Get all messages in the thread
        thread = service.users().threads().get(userId='me', id=thread_id).execute()
        
        email_summary = f"Number of unread emails: {unread_count}\n\n"
        
        for i, msg in enumerate(thread['messages']):
            # Get the full message data
            full_msg = service.users().messages().get(userId='me', id=msg['id'], format='raw').execute()
            msg_str = base64.urlsafe_b64decode(full_msg['raw'].encode('ASCII'))
            mime_msg = message_from_bytes(msg_str)

            # Extract and decode headers
            subject = decode_header(mime_msg['subject'])
            sender = decode_header(mime_msg['from'])
            to = decode_header(mime_msg['to'])
            cc = decode_header(mime_msg['cc']) if mime_msg['cc'] else 'N/A'
            date = mime_msg['date']

            # Extract body
            body = ""
            if mime_msg.is_multipart():
                for part in mime_msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode()
                        break
                    elif part.get_content_type() == "text/html":
                        html_body = part.get_payload(decode=True).decode()
                        body = html2text.html2text(html_body)
                        break
            else:
                body = mime_msg.get_payload(decode=True).decode()

            # Clean up the body
            body = clean_email_body(body)

            # Only include subject and Email ID for the most recent (last) email
            if i == len(thread['messages']) - 1:
              email_id = msg['id']
              email_summary += f"Subject: {subject}\n"
              email_summary += f"Email ID: {email_id}\n"

            email_summary += f"Date: {date}\n" \
                             f"From: {sender}\n" \
                             f"To: {to}\n" \
                             f"CC: {cc}\n" \
                             f"Body:\n{body}\n\n" \
                             f"{'='*25}\n\n"
        
        return email_summary

def clean_email_body(body: str) -> str:
    """
    Clean up the email body by removing quoted text and signatures.
    """
    # Remove any lines starting with '>' (quoted text)
    body = re.sub(r'^>.*$', '', body, flags=re.MULTILINE)
    
    # Remove any text after common reply indicators
    patterns = [
        r'\nOn\s+.*?wrote:.*',
        r'\nOn .+wrote:',
        r'\n-{3,}.*Original Message.*-{3,}',
        r'\nFrom:',
        r'\n-----',
        r'\n_+',  # Underscores are sometimes used as separators
        r'\nSent from my',
    ]
    for pattern in patterns:
        parts = re.split(pattern, body, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if parts:
            body = parts[0]

    # Remove extra newlines
    body = re.sub(r'\n{3,}', '\n\n', body)
    
    return body.strip()

def decode_header(header_value):
    """
    Decode email header value, handling non-ASCII characters.
    """
    decoded_parts = header.decode_header(header_value)
    decoded_value = ""
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            decoded_value += part.decode(encoding or 'utf-8')
        else:
            decoded_value += part
    return decoded_value
#read_email()

@debug_print
def mark_email_as_read(email_id: str) -> str:
  """
  Marks the specified email as read.
  """
  service = get_gmail_service()
  print(f"Marking email {email_id} as read...")
  try:
    service.users().messages().modify(
      userId='me',
      id=email_id,
      body={'removeLabelIds': ['UNREAD']}
    ).execute()
    return f"Email {email_id} marked as read."
  except Exception as e:
    return f"Failed to mark email {email_id} as read: {str(e)}"

#print(check_email())
#print(mark_email_as_read('190453f6c783f63c'))

@debug_print
def reply_to_email(
  email_id: str,
  subject: str,
  body: str,
  to_recipients: list[str],
  cc_recipients: list[str] = []
) -> str:
  """
  Replies to a specific email with the given subject and body.
  
  Args:
  email_id (str): The ID of the specific email to reply to.
  subject (str): The subject of the email.
  body (str): The body content of the email.
  to_recipients (list[str]): List of email addresses for 'To' field.
  cc_recipients (list[str], optional): List of email addresses for 'Cc' field.
  """
  try:
    print(f"Replying to email {email_id}")
    service = get_gmail_service()
    
    # Get the specific message
    message = service.users().messages().get(userId='me', id=email_id).execute()
    
    # Extract the Message-ID and Thread-ID of the original message
    headers = message['payload']['headers']
    message_id = next(header['value'] for header in headers if header['name'].lower() == 'message-id')
    thread_id = message['threadId']
    
    # Create the reply message
    reply = MIMEText(body)
    reply['Subject'] = subject
    reply['In-Reply-To'] = message_id
    reply['References'] = message_id

    # Set the From header with the display name and email address
    reply['From'] = formataddr((SECRETS['name'], SECRETS['email']))
    
    # Set 'To' recipients
    reply['To'] = ', '.join(to_recipients)
    
    # Set 'Cc' recipients if any
    if cc_recipients:
      reply['Cc'] = ', '.join(cc_recipients)
    
    # Create the raw message
    raw_message = base64.urlsafe_b64encode(reply.as_bytes()).decode('utf-8')
    
    # Send the message
    send_message = service.users().messages().send(
      userId='me',
      body={'raw': raw_message, 'threadId': thread_id}
    ).execute()
    
    return f"Email sent successfully. Message ID: {send_message['id']}"
  except Exception as e:
    return f"An error occurred: {str(e)}"

#print(reply_to_email('190453f6c783f63c', 'test email', 'Hi!', ['youremail@gmail.com']))

@debug_print
def create_calendar_invite(
  summary: str,
  start_time: str,
  end_time: str,
  attendees: list[str],
  timezone: str,
  description: str = "",
  location: str = ""
) -> str:
  """
  Creates a calendar invite.
  
  Args:
  summary (str): The title of the event.
  start_time (str): The start time of the event in ISO format (e.g., '2024-06-23T14:00:00').
  end_time (str): The end time of the event in ISO format.
  attendees (list[str]): List of email addresses.
  timezone (str): The timezone for the event.
  description (str, optional): The description or details of the event.
  location (str, optional): The location of the event.
  """
  try:

    print(f"Creating calendar invite...")
    service = get_calendar_service()
    
    # Create the event dictionary
    event = {
      'summary': summary,
      'location': location,
      'description': description,
      'start': {
        'dateTime': start_time,
        'timeZone': timezone
      },
      'end': {
        'dateTime': end_time,
        'timeZone': timezone
      },
      'attendees': [{'email': attendee} for attendee in attendees],
      'reminders': {
        'useDefault': False,
        'overrides': [
          {'method': 'email', 'minutes': 24 * 60},
          {'method': 'popup', 'minutes': 10},
        ],
      },
    }

    event = service.events().insert(calendarId='primary', body=event, sendUpdates='all').execute()
    return f"Calendar invite created successfully. Event ID: {event.get('id')}"
  except Exception as e:
    return f"An error occurred while creating the calendar invite: {str(e)}"
#print(create_calendar_invite('programmatic event, delete', '2024-06-25T14:00:00', '2024-06-25T15:00:00', ['youremail@gmail.com'], 'Asia/Shanghai'))

#from playwright.sync_api import sync_playwright
import textwrap

def execute_web_action(playwright_code: str) -> str:
    """
    Executes the given Playwright Python code and returns the result.
    
    Args:
    playwright_code (str): A string containing valid Playwright Python code.
    
    Returns:
    str: The result of the web action, or an error message if execution failed.
    """
    try:
        # Remove any common leading whitespace from every line
        dedented_code = textwrap.dedent(playwright_code)
        
        # Wrap the provided code in a function with proper indentation
        wrapped_code = f"""
def run_action():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
{textwrap.indent(dedented_code, '        ')}
        browser.close()
        return result  # Assume the code sets a 'result' variable

result = run_action()
"""
        print("Running web action...")
        print(wrapped_code)
        # Execute the wrapped code
        loc = {}
        exec(wrapped_code, globals(), loc)
        return str(loc['result'])
    except Exception as e:
        return f"Error executing web action: {str(e)}"

playwright_code = """
page.goto("https://maraoz.com")
screenshot = page.screenshot(path="maraoz_screenshot.png")
result = "Screenshot saved as maraoz_screenshot.png"
"""
#print(execute_web_action(playwright_code))

def explain(r):
  #print(f'explaining reply of length {len(r.content)}')
  for o in r.content:
    if o.type == 'text':
      print(">>>", o.text)
    elif o.type == 'tool_use':
      print(f'FUNCTION CALL ---> {o.name}({o.input})')
    else:
      print("NEW CASE, CHECK THIS OUT!!!!")
      print(o)


today = datetime.now().strftime("%A, %B %d, %Y")

chat = Chat(
  model, 
  tools=[notify_owner, http_request, check_calendar_availability, read_email, mark_email_as_read, reply_to_email, create_calendar_invite],
  sp=f"You're a helpful and concise assistant. The current date is {today}."
)

#answer = chat.toolloop("Write a poem about today's date and send it via email. The body should only contain the poem and no additional prose. Pick the subject yourself.")

#answer = chat.toolloop("read the top 3 stories from hacker news (https://news.ycombinator.com/) and email me a summary of each. You should actually read each link, not only the titles. subject should be 'HN Update'")

main_prompt = f"""
Your name is {SECRETS['name']} and you are a scheduling assistant for me, {SECRETS['user_name']}.
Here's how you should help me with scheduling.

(1) Read your inbox for emails from me asking to schedule meetings. 
If you have new email and it's about scheduling, read the whole thread.

(1a) If it's a new meeting, check my calendar availability according to the context in that email. Try to check at a range of at least 1 week, not just 2 days, unless the context requires it.
Weeks start on Monday.

(1b) If a schedule has already been proposed, first check my availability and if I'm free proceed directly to step 3 without proposing new times unless needed.
If someone proposed times to meet, bear in mind their timezone when checking my availability! If you don't know, ask for clarification. (eg: if someone replies "what about tomorrow 4pm" and you have no information about their timezone, you should ask.)

(2) Then, propose a schedule by replying directly to the email thread.
Only propose a meeting schedule if no option that works for everytone has already been sent (otherwise go to 3).
Only send 1 to 3 options, don't reveal my whole availability.
Try to make the options varied (eg: some in the morning, some in the afternoon).
The message should be professional but as short as possible.
When replying, always include all participants from the original email thread (To and CC fields) to ensure everyone is kept in the loop.
My current timezone is {SECRETS['user_timezone']}. 
Always mention the timezone (in human readable format eg: GMT+8 or Uruguay time) when proposing meeting times. If possible, convert times to the recipient's timezone if it's mentioned or can be inferred from the email thread.
Never propose a time that is outside of the 10am-11pm range for someone on the thread. (eg: don't propose a time which is 5am for one participant)

(3) If a meeting time has been agreed upon by the other party and I still have the time available, create a calendar invite for the meeting using the create_calendar_invite function.
Never create a calendar invite without checking my availability first!
Be careful to use the exact time that has been agreed.
The meeting name should be "$OWNER_NAME <> $OTHER_NAME" for two people meetings.
If more than 2 people are involved, pick a relevant meeting name according to context.
Default to 45' meeting time if not specified.

(4) Finally, mark the received email as read on your inbox to prevent double-processing.

If I'm not free or the email is not about scheduling, wait for further instructions by outputting "BACK TO SLEEP..." with no further prose.
"""

#read_email();

n = get_unread_count()
if n > 0:
  pass
  chat.toolloop(main_prompt, trace_func=explain)
else:
  print("No unread emails...")
