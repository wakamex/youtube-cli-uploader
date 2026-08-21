"""Authorize the uploader with a YouTube channel."""

import argparse
import os
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

DEFAULT_CONFIG = Path("~/.config/youtube-api-uploader").expanduser()
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--client-secrets",
        type=Path,
        default=DEFAULT_CONFIG / "client_secret.json",
        help="OAuth desktop client JSON downloaded from Google Cloud",
    )
    parser.add_argument(
        "--token",
        type=Path,
        default=DEFAULT_CONFIG / "token.json",
        help="Where to save the authorized user token",
    )
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.client_secrets.is_file():
        raise FileNotFoundError(args.client_secrets)

    flow = InstalledAppFlow.from_client_secrets_file(args.client_secrets, SCOPES)
    credentials = flow.run_local_server(
        host=args.host,
        port=args.port,
        open_browser=not args.no_browser,
        access_type="offline",
        prompt="consent",
        authorization_prompt_message="Open this URL to authorize the uploader:\n{url}",
        success_message="YouTube authorization completed. You may close this tab.",
    )

    args.token.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = args.token.with_suffix(args.token.suffix + ".temporary")
    temporary.write_text(credentials.to_json())
    os.chmod(temporary, 0o600)
    os.replace(temporary, args.token)
    os.chmod(args.token, 0o600)
    print(f"Authorization saved to {args.token}")

    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    response = (
        youtube.channels().list(part="id,snippet", mine=True).execute(num_retries=5)
    )
    channels = response.get("items", [])
    if not channels:
        raise RuntimeError("The authorized account does not have a YouTube channel")
    for channel in channels:
        channel_id = channel["id"]
        print(f"Channel: {channel['snippet']['title']}")
        print(f"Channel ID: {channel_id}")
        print(f"Channel URL: https://www.youtube.com/channel/{channel_id}")


if __name__ == "__main__":
    main()
