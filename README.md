# claudette-scheduling-agent

A Claude-based scheduling assistant that automates email responses and calendar management using Anthropic's API.

## Overview

claudette-scheduling-agent acts as a personal scheduling assistant.
It integrates with your inbox and calendar to automatically handle meeting requests, propose suitable meeting times, and create calendar invites.

Key features:
- Just add your bot to an email thread to begin (you'll need to create a new Gmail account)
- Reads and processes emails related to scheduling
- Checks calendar availability
- Proposes meeting times based on context
- Creates calendar invites
- Handles email responses professionally

## Prerequisites

- Python 3.7+
- Two Google accounts:
  1. Your personal Google account with Calendar access
  2. A new Google account for the assistant bot with Gmail access
- Anthropic API key for Claude AI model

## Setup

1. Clone the repository:
   ```
   git clone https://github.com/maraoz/claudette-scheduling-agent.git
   cd claudette-scheduling-agent
   ```

2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

3. Set up Google API credentials:
   a. For your personal Google account (Calendar API):
      - Go to the [Google Cloud Console](https://console.cloud.google.com/)
      - Create a new project
      - Enable the Google Calendar API
      - Create credentials (OAuth 2.0 Client ID) and save as `credentials.json` in project folder
      - Add your **personal gmail** as a test user.
      - First time you run `main.py` you'll be prompted to connect your go

   b. For the assistant's Google account (Gmail API):
      - Create a new Gmail account for the assistant bot
      - Go to the [Google Cloud Console](https://console.cloud.google.com/)
      - Enable the Gmail API
      - Add your **assistant's gmail** as a test user.

4. Create a `secrets.json` file in the project directory with the following structure:
   ```json
   {
    "email": "your_bot_gmail_address@gmail.com",
    "name": "Assistant Name",
    "user_email": "your_personal_gmail@gmail.com",
    "user_name": "Your Name",
    "user_timezone": "America/New_York",
    "ANTHROPIC_API_KEY": "your_anthropic_api_key",
   }
   ```

## Usage

You can either run it once:
```sh
python main.py
```

Or leave it running every 10 minutes:
```sh
./run.sh
```

On first run, you'll need to authorize the application:
1. For Gmail access: You'll be prompted to log in with the assistant bot's Google account
2. For Calendar access: You'll be prompted to log in with your personal Google account
3. Remember you need to add both gmail addresses as test users in your Google Console project (I'm repeating myself here because you probably skipped the instructions above)

The agent will then:
1. Check for unread emails in the assistant's inbox
2. Process scheduling-related emails
3. Check your personal calendar availability
4. Propose meeting times or create calendar invites as appropriate
5. Mark processed emails as read

## Configuration

Adjust the `main_prompt` in the script and `secrets.json` to customize the behavior of the scheduling agent. You can modify timezone settings, scheduling preferences, and email response styles.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
If this README has any mistakes, please contribute a fix! I relied heavily on Claiude to write it, so it will probably contain errors. Sorry for that! I thought it'd be better to publish something rough than not publish it :)

## License

[MIT License](LICENSE)

## Disclaimer

This tool accesses and modifies your email and calendar. Use it at your own risk and make sure you understand the implications before running it on your personal or work accounts. Always review the actions taken by the bot to ensure they align with your intentions.

