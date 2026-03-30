#!/usr/bin/env python3
"""
Re-authenticate for YouTube comments + video updates.
Run this interactively (it opens a browser for OAuth consent).

    python3 yt_reauth_comments.py

This creates ~/yt_token_comments.pickle with youtube.force-ssl scope.
Then run yt_pinned_comments.py which uses this token.
"""
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
CLIENT_SECRET = os.path.expanduser("~/client_secret.json")
TOKEN_PATH = os.path.expanduser("~/yt_token_comments.pickle")

flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
creds = flow.run_local_server(port=8080)

with open(TOKEN_PATH, "wb") as f:
    pickle.dump(creds, f)

print(f"✅ Token saved to {TOKEN_PATH}")
print("Now run: python3 automation/yt_pinned_comments.py")
