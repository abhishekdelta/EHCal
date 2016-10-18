import sys
sys.path.insert(1, '/Library/Python/2.7/site-packages')

import httplib2
import os
import requests

from apiclient import discovery
from datetime import datetime
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# EH CONFIG
CALENDAR_NAME = 'EventsHigh Calendar - Bangalore'
CITY_NAME = 'bangalore'
FEATURED = False # Change to True to only populate featured events
CATEGORIES = ['parties']
POPULATE_DATES = ['2016-10-17', '2016-10-18', '2016-10-19', '2016-10-20', '2016-10-21']

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/calendar'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Calendar API Python Quickstart'

def get_credentials():
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'calendar-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def create_calendar(service, title, timezone='America/Los_Angeles'):
    calendar = {
        'summary': title,
        'timeZone': timezone
    }
    created_calendar = service.calendars().insert(body=calendar).execute()
    print 'Calendar created: %s' % (created_calendar['id'])
    return created_calendar['id']

def insert_event(service, event_info, cal_id): 
    event = {
      'summary': event_info['title'],
      'location': event_info['address'],
      'description': event_info['description'],
      'start': {
        'dateTime': event_info['startTime'],
        'timeZone': event_info['startTimeTZ']
      },
      'end': {
        'dateTime': event_info['endTime'],
        'timeZone': event_info['endTimeTZ']
      }
    }

    event = service.events().insert(calendarId=cal_id, body=event).execute()
    print 'Event created: %s' % (event.get('htmlLink'))

def list_calendars(service):
    page_token = None
    cals = []
    while True:
      calendar_list = service.calendarList().list(pageToken=page_token).execute()
      for calendar_list_entry in calendar_list['items']:
        cals.append({'title':calendar_list_entry['summary'], 
                     'id': calendar_list_entry['id']})
      page_token = calendar_list.get('nextPageToken')
      if not page_token:
        break
    return cals

def getDateTime(date_str, time_str):
    if not date_str:
        return ''
    if not time_str:
        time_str = '23:59:00'
    return datetime.strptime(date_str[:10] + '@' + time_str, '%Y-%m-%d@%H:%M:%S')

def is_featured(event_json):
    return len(filter(lambda x: x['tag'] == 'featured', event_json['tags'])) > 0

def main():
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    # now = datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    # print('Getting the upcoming 10 events')
    # eventsResult = service.events().list(
    #     calendarId='primary', timeMin=now, maxResults=10, singleEvents=True,
    #     orderBy='startTime').execute()
    # events = eventsResult.get('items', [])

    # if not events:
    #     print('No upcoming events found.')
    # for event in events:
    #     start = event['start'].get('dateTime', event['start'].get('date'))
    #     print(start, event['summary'])

    # check if cal already exists, if not create it
    cal = filter(lambda x: x['title'] == CALENDAR_NAME, list_calendars(service))
    cal_id = ""
    if not cal:
        # create cal
        cal_id = create_calendar(service, CALENDAR_NAME)
        # insert cal into user
        created_calendar_list_entry = service.calendarList().insert(body={'id':cal_id}).execute()
    else:
        cal_id = cal[0]['id']
        print "Alreday found calendar %s with id %s" % (CALENDAR_NAME, cal_id)

    # insert event
    # event_info = {
    #     'title': 'Hello World',
    #     'address': 'Middle of the ocean',
    #     'description': 'Life, Universe & Everything',
    #     'startTime': formatDateTime('2016-10-13:12-00', '21:00:00'),
    #     'startTimeTZ': 'Asia/Kolkata',
    #     'endTime': formatDateTime('2016-10-13:12-00', None),
    #     'endTimeTZ': 'Asia/Kolkata'
    # }
    for date in POPULATE_DATES:
        data = requests.get('https://api.eventshigh.com/api/date/%s/%s' % (CITY_NAME, date)).json()
        print "For date %s, inserting %d events.. " % (date, len(data['upcoming_events']))
        for event in data['upcoming_events']:
            if not event['date']:
                print "Skipping event %s (%s) because time is missing!" % (event['title'], event['id'])
                continue

            if FEATURED && !is_featured(event):
                print "Skipping event %s (%s) because its not featured!" % (event['title'], event['id'])
                continue

            start_date = getDateTime(event['date'], event['start_time'] or '00:00:00')
            end_date = getDateTime(event['end_date'], event['end_time'] or '23:59:59')
            if start_date > end_date:
                print "Skipping event %s (%s) because of bad time data!" % (event['title'], event['id'])
                continue

            event_info = {
                'title': event['title'],
                'address': event['venue'],
                'description': event['description'],
                'startTime': start_date.isoformat(),
                'startTimeTZ': 'Asia/Kolkata',
                'endTime': end_date.isoformat(),
                'endTimeTZ': 'Asia/Kolkata'
            }
            insert_event(service, event_info, cal_id)

if __name__ == '__main__':
    main()
