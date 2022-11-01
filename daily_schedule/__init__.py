import os
import json
import logging
import httplib2
import azure.functions as func

from string import Template
import pytz
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from oauth2client import client, GOOGLE_TOKEN_URI

def main(timerRequest: func.TimerRequest) -> None:
    utcnow = datetime.utcnow().isoformat()
    logging.info(f'Python timer trigger function ran at {utcnow}')

    if timerRequest.past_due:
        logging.info('The timer is past due!')

    calendar = getCalendar()
    logging.info(f'calendar: {calendar}')

    body = getRequestBody(calendar)
    logging.info(f'request body: {body}')
    
    resp, content = httplib2.Http().request(
        uri = os.environ['WEBHOOK'], 
        method = 'POST', 
        body = body, 
        headers = {'Content-Type': 'application/json'}
    )
    if resp.status != 200:
        logging.error(f'resp: {resp}, content: {content}')

def getFormatedEvent(event):
    templateString = '>[**$summary**]($htmlLink)\n>**When:** $startTime - $endTime$where'
    locations = getLocations(event)
    where = f'\n>**Where:** {",".join(locations)}' if len(locations) > 0 else ''
    startTime = datetime.fromisoformat(event['start']['dateTime']).strftime('%-I:%M%p')
    endTime = datetime.fromisoformat(event['end']['dateTime']).strftime('%-I:%M%p')
    return Template(templateString).substitute(
        summary=event['summary'], 
        htmlLink=event['htmlLink'], 
        startTime=startTime, 
        endTime=endTime,
        where=where
    )

def getLocations(event):
    locations = []
    if 'location' in event:
        locations.append(event['location'])
    if 'conferenceData' in event:
        video = next((f'[{x["uri"]}]({x["uri"]})' for x in event['conferenceData']['entryPoints'] if x['entryPointType'] == 'video'), None)
        if video is not None:
            locations.append(video)
    return locations

def getTodayOfStartAndEnd(timeZone):
    today = datetime.now(tz=pytz.timezone(timeZone))
    start = today.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(1)
    return start, end

def getCredentials():
    clientId = os.environ['CLIENT_ID']
    clientSecret = os.environ['CLIENT_SECRET']
    refreshToken = os.environ['REFRESH_TOKEN']
    credentials = client.GoogleCredentials(
        access_token='', 
        client_id=clientId, 
        client_secret=clientSecret, 
        refresh_token=refreshToken, 
        token_expiry=None, 
        token_uri=GOOGLE_TOKEN_URI, 
        user_agent='daily-reminder'
    )
    credentials.refresh(httplib2.Http())
    return credentials

def getRequestBody(calendar):
    calendar['items'].sort(key=lambda event: datetime.fromisoformat(event['start']['dateTime']))
    formatedEvents = map(getFormatedEvent, calendar['items'])
    content = '\n\n'.join(formatedEvents)
    message = {"msgtype": "markdown", "markdown": {"content": content}}
    return json.dumps(message)

def getCalendar():
    timeZone = os.environ['TIME_ZONE']
    startTime, endTime = getTodayOfStartAndEnd(timeZone)
    service = build('calendar', 'v3', credentials=getCredentials())
    return service.events().list(
        calendarId='primary', 
        timeMin=startTime.isoformat(), 
        timeMax=endTime.isoformat(),
        timeZone=timeZone,
        showDeleted=False, 
        singleEvents=True
    ).execute()