"""YouTube Live API OAuth setup.

Run this in a browser-accessible environment. It will open a browser
for Google OAuth authorization, then save the token for YouTube API access.
"""
import json
import os
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

PROJECT = Path(__file__).parent.parent
TOKEN_PATH = PROJECT / "config" / "youtube_token.json"
# Reuse existing Google OAuth client credentials
CLIENT_SECRETS = Path("/home/agent/.config/gws/client_secret.json")


def authenticate():
    creds = None

    # Load existing token if available
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    # Refresh or get new token
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            if not CLIENT_SECRETS.exists():
                print(f"ERROR: No client secrets at {CLIENT_SECRETS}")
                print("You need a Google OAuth client ID. Get one from:")
                print("  https://console.cloud.google.com/apis/credentials")
                print("Download the JSON and place it at the path above.")
                return None

            print("Opening browser for YouTube API authorization...")
            print("Please authorize access in the browser window.")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRETS), SCOPES
            )
            creds = flow.run_local_server(port=8099, open_browser=True)

        # Save token
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
        print(f"Token saved to {TOKEN_PATH}")

    return creds


def test_api(creds):
    """Quick test — list live broadcasts."""
    youtube = build("youtube", "v3", credentials=creds)

    # List active broadcasts
    resp = youtube.liveBroadcasts().list(
        part="id,snippet,status",
        broadcastStatus="active",
    ).execute()

    broadcasts = resp.get("items", [])
    if broadcasts:
        for b in broadcasts:
            print(f"Active broadcast: {b['snippet']['title']} (ID: {b['id']}, status: {b['status']['lifeCycleStatus']})")
    else:
        print("No active broadcasts found.")

    # List upcoming
    resp2 = youtube.liveBroadcasts().list(
        part="id,snippet,status",
        broadcastStatus="upcoming",
    ).execute()
    for b in resp2.get("items", []):
        print(f"Upcoming: {b['snippet']['title']} (ID: {b['id']})")

    return youtube


if __name__ == "__main__":
    creds = authenticate()
    if creds:
        print("\nTesting YouTube API access...")
        test_api(creds)
        print("\nYouTube API setup complete!")
