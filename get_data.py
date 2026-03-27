import requests
import json
from config import *

def get_events():
    response = requests.get(f"{KPI_API_URL}/events")
    events = json.loads(response.text)

    return events

def get_event(event_id):
    headers = {
        "authorization": f"Bearer {AUTH_TOKEN}",
    }

    response = requests.get(f"{KPI_API_URL}/events/{event_id}", headers=headers)
    event = json.loads(response.text)

    return event


def get_locations(event_id):
    response = requests.get(f"{KPI_API_URL}/locations/event/{event_id}")
    locations = json.loads(response.text)

    return locations

def get_location(location_id):
    headers = {
        "authorization": f"Bearer {AUTH_TOKEN}",
    }

    response = requests.get(f"{KPI_API_URL}/locations/{location_id}", headers=headers)
    event = json.loads(response.text)

    return event


def get_leagues(location_id):
    response = requests.get(f"{KPI_API_URL}/leagues/location/{location_id}")
    leagues = json.loads(response.text)

    return leagues

def get_league(league_id):
    headers = {
        "authorization": f"Bearer {AUTH_TOKEN}",
    }

    response = requests.get(f"{KPI_API_URL}/leagues/{league_id}", headers=headers)
    league = json.loads(response.text)

    return league


def get_teams(league_id):
    headers = {
        "authorization": f"Bearer {AUTH_TOKEN}"
    }

    response = requests.get(f"{KPI_API_URL}/teams/league/{league_id}", headers=headers)
    teams = json.loads(response.text)

    return teams

def get_team(team_id):
    headers = {
        "authorization": f"Bearer {AUTH_TOKEN}",
    }

    response = requests.get(f"{KPI_API_URL}/teams/{team_id}", headers=headers)
    team = json.loads(response.text)

    return team

