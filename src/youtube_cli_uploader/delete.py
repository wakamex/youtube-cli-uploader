"""Delete a video through the YouTube Data API."""

import argparse
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from youtube_cli_uploader.upload import DEFAULT_TOKEN, require_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("video_id")
    parser.add_argument("--token", type=Path, default=DEFAULT_TOKEN)
    return parser.parse_args()


def delete_video(youtube, video_id: str) -> None:
    youtube.videos().delete(id=video_id).execute(num_retries=5)
    print(f"Video deleted: {video_id}", flush=True)


def main() -> None:
    args = parse_args()
    require_file(args.token)
    credentials = Credentials.from_authorized_user_file(args.token)
    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    delete_video(youtube, args.video_id)


if __name__ == "__main__":
    main()
