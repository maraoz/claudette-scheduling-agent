
# ClaudeBot

### Installation

Requirements: 
- python 3

```
pip install -r requirements.txt
```

You also need to get the following files:
- secrets.json (see sample_secrets.json)
- token_calendar.json (download from google console, calendar API)
- token_gmail.json (download from google console, Gmail API)
- credentials.json (download from google console)

### Running
You can either run it once:
```sh
python main.py
```

Or leave it running every 10 minutes:
```sh
./run.sh
```