from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
import os

def refresh_or_create_token(token_file: str, scopes: list):
  creds = None
  if os.path.exists(token_file):
    creds = Credentials.from_authorized_user_file(token_file, scopes)
  
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      try:
        creds.refresh(Request())
      except RefreshError:
        print(f"Failed to refresh token in {token_file}. Initiating new authentication flow.")
        creds = None
    
    if not creds:
      flow = InstalledAppFlow.from_client_secrets_file('credentials.json', scopes)
      creds = flow.run_local_server(port=0)
    
    # Save the credentials for the next run
    with open(token_file, 'w') as token:
      token.write(creds.to_json())
  
  print(f"Token in {token_file} has been refreshed or recreated.")

def main():
  GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
  CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']
  
  print("Refreshing or recreating Gmail token...")
  refresh_or_create_token('token_gmail.json', GMAIL_SCOPES)
  
  print("Refreshing or recreating Calendar token...")
  refresh_or_create_token('token_calendar.json', CALENDAR_SCOPES)
  
  print("Token refresh or recreation complete.")

if __name__ == "__main__":
  main()