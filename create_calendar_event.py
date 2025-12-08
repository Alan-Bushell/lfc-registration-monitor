import os
from datetime import timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]
SERVICE_ACCOUNT_FILE = 'service_account.json'

# Get the target calendar ID from environment variables
TARGET_CALENDAR_ID = os.environ.get('TARGET_CALENDAR_ID')

if not TARGET_CALENDAR_ID:
    # Fallback for local testing if not set, or raise an error
    print("Warning: TARGET_CALENDAR_ID environment variable not set.")

def get_calendar_service():
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"Error: {SERVICE_ACCOUNT_FILE} not found.")
        return None
    
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("calendar", "v3", credentials=creds)

def create_event(summary, start_time, end_time, description=None, color_id='11'):
    """
    Creates a Google Calendar event using a Service Account.
    color_id '11' is Tomato (Red).
    """
    service = get_calendar_service()
    if not service:
        return

    # Determine which calendar to use
    calendar_id = 'primary'
    
    if TARGET_CALENDAR_ID:
        calendar_id = TARGET_CALENDAR_ID
    else:
        # Try to auto-detect if not specified
        try:
            calendar_list = service.calendarList().list().execute()
            for entry in calendar_list.get('items', []):
                cal_id = entry['id']
                if not cal_id.endswith('.iam.gserviceaccount.com') and '@' in cal_id:
                    calendar_id = cal_id
                    break
        except Exception:
            pass

    if calendar_id == 'primary' and not TARGET_CALENDAR_ID:
         print(f"Note: Using Service Account's primary calendar.")
         print(f"To use your personal calendar, please edit create_calendar_event.py and set TARGET_CALENDAR_ID = 'your_email@gmail.com'")

    # Check for duplicates
    try:
        # Search for events with the same summary within a narrow time window (+/- 1 day).
        # This prevents matching events from previous seasons (years ago).
        # We append 'Z' to satisfy the API's requirement for a timezone offset.
        time_min = (start_time - timedelta(days=1)).isoformat() + 'Z'
        time_max = (end_time + timedelta(days=1)).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId=calendar_id,
            q=summary,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        existing_events = events_result.get('items', [])

        for existing_event in existing_events:
            # Strict check on summary
            if existing_event.get('summary') == summary:
                print(f"Event '{summary}' already exists. Skipping creation.")
                return
    except Exception as e:
        print(f"Warning: Could not check for duplicates: {e}")

    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'Europe/London',
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'Europe/London',
        },
        'colorId': color_id,
    }

    try:
        print(f"Creating event '{summary}' in calendar: {calendar_id}")
        event = service.events().insert(calendarId=calendar_id, body=event).execute()
        print(f"Event created: {event.get('htmlLink')}")
    except Exception as e:
        print(f"An error occurred creating the event: {e}")
        if "Not Found" in str(e) or "404" in str(e):
             print(f"Double check that you have shared your calendar with: bot-user@lfc-registration-monitor.iam.gserviceaccount.com")
