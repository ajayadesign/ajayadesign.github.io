#!/usr/bin/env python3
"""
Add pinned comments and update descriptions for all YouTube videos
on the @AJDESIGN-y8m channel.

Usage:
    python3 yt_pinned_comments.py

Requirements:
    pip install google-api-python-client google-auth google-auth-oauthlib
"""

import os
import pickle
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
CHANNEL_ID = "UCUDAzAh-qpKR4z1b9KaHNsg"
TOKEN_PATH = os.path.expanduser("~/yt_token_comments.pickle")
CLIENT_SECRET = os.path.expanduser("~/client_secret.json")
RESULTS_FILE = os.path.expanduser("~/video-uploads/pinned_comments_results.json")

COURSE_URL = "https://ajayadesign.github.io/3D-print/"

PINNED_COMMENT = (
    "🎓 Want the full 3D Print Academy course? 43 lessons, 7 modules, STL files included\n"
    f"→ {COURSE_URL}\n\n"
    f"📥 Download a FREE magnet frame STL → {COURSE_URL}\n\n"
    "👍 Like & Subscribe for more 3D printing tips!"
)

DESCRIPTION_PREFIX = (
    f"🎓 Full course: {COURSE_URL}\n\n"
)


def get_authenticated_service():
    """Authenticate and return YouTube API service."""
    creds = None

    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as f:
            creds = pickle.load(f)

    # Check if existing creds have the right scopes
    if creds and hasattr(creds, 'scopes') and creds.scopes and not set(SCOPES).issubset(creds.scopes):
        print("⚠️  Existing token lacks required scopes. Re-authenticating...")
        creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "wb") as f:
            pickle.dump(creds, f)

    return build("youtube", "v3", credentials=creds)


def get_all_video_ids(youtube):
    """Get all video IDs from the channel's uploads playlist."""
    # Get uploads playlist ID
    ch_response = youtube.channels().list(
        part="contentDetails", id=CHANNEL_ID
    ).execute()

    uploads_playlist = ch_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    video_ids = []
    next_page = None

    while True:
        pl_response = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist,
            maxResults=50,
            pageToken=next_page,
        ).execute()

        for item in pl_response["items"]:
            vid = item["snippet"]["resourceId"]["videoId"]
            title = item["snippet"]["title"]
            video_ids.append({"id": vid, "title": title})

        next_page = pl_response.get("nextPageToken")
        if not next_page:
            break

    return video_ids


def add_pinned_comment(youtube, video_id):
    """Insert a comment and pin it (set as channel's top comment)."""
    # Insert comment
    comment_response = youtube.commentThreads().insert(
        part="snippet",
        body={
            "snippet": {
                "videoId": video_id,
                "topLevelComment": {
                    "snippet": {
                        "textOriginal": PINNED_COMMENT,
                    }
                },
            }
        },
    ).execute()

    comment_id = comment_response["snippet"]["topLevelComment"]["id"]

    # Pin it (moderator action — set as held for review then approve, or use
    # the setModerationStatus to published + banAuthor=false)
    # Actually: YouTube API doesn't have a direct "pin" endpoint.
    # The workaround: use comments().setModerationStatus or the
    # community captions approach. Unfortunately, pinning comments via API
    # is not officially supported. The comment will still appear as the
    # channel owner's comment (shown prominently).
    #
    # Note: As of 2024, the YouTube Data API v3 does NOT support pinning
    # comments programmatically. The comment will be posted as the channel
    # owner (which YouTube shows at the top by default for channel owners),
    # but true "pin" requires manual action in YouTube Studio.

    return comment_id


def update_video_description(youtube, video_id):
    """Prepend course link to video description if not already there."""
    video_response = youtube.videos().list(
        part="snippet", id=video_id
    ).execute()

    if not video_response["items"]:
        return False

    snippet = video_response["items"][0]["snippet"]
    current_desc = snippet.get("description", "")

    if COURSE_URL in current_desc:
        return "already_has_link"

    new_desc = DESCRIPTION_PREFIX + current_desc

    snippet["description"] = new_desc
    # categoryId is required for update
    category_id = snippet.get("categoryId", "27")  # 27 = Education

    youtube.videos().update(
        part="snippet",
        body={
            "id": video_id,
            "snippet": {
                "title": snippet["title"],
                "description": new_desc,
                "categoryId": category_id,
                "tags": snippet.get("tags", []),
            },
        },
    ).execute()

    return True


def main():
    print("🔐 Authenticating with YouTube API...")
    youtube = get_authenticated_service()

    print("📋 Fetching all videos from channel...")
    videos = get_all_video_ids(youtube)
    print(f"   Found {len(videos)} videos\n")

    results = {}

    for v in videos:
        vid_id = v["id"]
        title = v["title"]
        print(f"▶ Processing: {title} ({vid_id})")
        result = {"title": title, "comment": None, "description": None}

        # Add comment
        try:
            comment_id = add_pinned_comment(youtube, vid_id)
            result["comment"] = f"✅ Posted (ID: {comment_id}) — NOTE: pin manually in YouTube Studio"
            print(f"   💬 Comment posted (pin manually in Studio)")
        except Exception as e:
            result["comment"] = f"❌ Failed: {e}"
            print(f"   ❌ Comment failed: {e}")

        # Update description
        try:
            desc_result = update_video_description(youtube, vid_id)
            if desc_result == "already_has_link":
                result["description"] = "⏭️ Already has course link"
                print(f"   📝 Description already has link")
            else:
                result["description"] = "✅ Updated"
                print(f"   📝 Description updated")
        except Exception as e:
            result["description"] = f"❌ Failed: {e}"
            print(f"   ❌ Description failed: {e}")

        results[vid_id] = result
        print()

    # Save results
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)

    # Summary
    comment_ok = sum(1 for r in results.values() if r["comment"] and r["comment"].startswith("✅"))
    desc_ok = sum(1 for r in results.values() if r["description"] and (r["description"].startswith("✅") or r["description"].startswith("⏭️")))
    total = len(results)

    print("=" * 50)
    print(f"📊 Results: {total} videos processed")
    print(f"   💬 Comments posted: {comment_ok}/{total}")
    print(f"   📝 Descriptions updated: {desc_ok}/{total}")
    print(f"   📁 Full results: {RESULTS_FILE}")
    print()
    print("⚠️  IMPORTANT: YouTube API does not support pinning comments programmatically.")
    print("   Go to YouTube Studio → each video → Comments → pin the comment manually.")
    print("   Channel owner comments appear near the top by default, but pinning")
    print("   ensures they stay at #1 position.")


if __name__ == "__main__":
    main()
