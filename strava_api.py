# strava_api.py
import requests, time
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ⚠️ Replace with your actual credentials
CLIENT_ID = "178138"
CLIENT_SECRET = "b097aea2c9f6a09098da713e54313262dd22e885"
REFRESH_TOKEN = "f990297ce6df4e913f02b168f0b07a174492871b"

AUTH_URL = "https://www.strava.com/oauth/token"
BASE_URL = "https://www.strava.com/api/v3"


def get_access_token():
    """Refresh and return a valid Strava access token."""
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': REFRESH_TOKEN,
        'grant_type': "refresh_token",
    }
    res = requests.post(AUTH_URL, data=payload, verify=False)
    return res.json()["access_token"]


def get_all_activities(limit=5):
    """Fetch your recent activities (for testing)."""
    token = get_access_token()
    headers = {'Authorization': f'Bearer {token}'}
    params = {'per_page': limit, 'page': 1}
    response = requests.get(f"{BASE_URL}/athlete/activities", headers=headers, params=params)
    return response.json()


def get_activity_details(activity_id):
    """Fetch detailed info about one activity (includes segment_efforts)."""
    token = get_access_token()
    headers = {'Authorization': f'Bearer {token}'}
    url = f"{BASE_URL}/activities/{activity_id}"
    return requests.get(url, headers=headers).json()


def get_segment_details(segment_id):
    """Fetch info about one segment (includes KOM/QOM times)."""
    token = get_access_token()
    headers = {'Authorization': f'Bearer {token}'}
    url = f"{BASE_URL}/segments/{segment_id}"
    return requests.get(url, headers=headers).json()

def get_segment_polyline(segment_id):
    """Fetch the segment polyline from Strava API."""
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BASE_URL}/segments/{segment_id}"
    resp = requests.get(url, headers=headers)

    # Handle rate limit (HTTP 429)
    if resp.status_code == 429:
        print("Rate limit reached, waiting 15 minutes...")
        time.sleep(15 * 60)
        return get_segment_polyline(segment_id)

    resp.raise_for_status()
    data = resp.json()

    return data["map"]["polyline"] if "map" in data and data["map"].get("polyline") else None