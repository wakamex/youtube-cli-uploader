"""Upload a video and its optional assets through the YouTube Data API."""

import argparse
import json
import os
import time
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

DEFAULT_TOKEN = Path("~/.config/youtube-api-uploader/token.json").expanduser()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--description-file", type=Path, required=True)
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--thumbnail", type=Path)
    parser.add_argument("--captions", type=Path)
    parser.add_argument("--caption-language", default="en")
    parser.add_argument("--category", default="28")
    parser.add_argument("--language", default="en")
    parser.add_argument(
        "--privacy", choices=("private", "unlisted", "public"), default="private"
    )
    parser.add_argument("--made-for-kids", action="store_true")
    parser.add_argument("--contains-synthetic-media", action="store_true")
    parser.add_argument("--token", type=Path, default=DEFAULT_TOKEN)
    parser.add_argument(
        "--state",
        type=Path,
        help="Upload state file; defaults to VIDEO.youtube-upload.json",
    )
    parser.add_argument("--processing-timeout", type=int, default=3600)
    parser.add_argument("--caption-timeout", type=int, default=300)
    return parser.parse_args()


def require_file(path: Path | None) -> None:
    if path is not None and not path.is_file():
        raise FileNotFoundError(path)


def state_path_for(args: argparse.Namespace) -> Path:
    return args.state or Path(f"{args.video}.youtube-upload.json")


def load_state(path: Path, video: Path) -> dict:
    state = json.loads(path.read_text()) if path.exists() else {}
    video_path = str(video.resolve())
    recorded_path = state.get("video_path")
    if recorded_path and recorded_path != video_path:
        raise ValueError(
            f"{path} belongs to {recorded_path}; use a different --state path"
        )
    state["video_path"] = video_path
    return state


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".temporary")
    temporary.write_text(json.dumps(state, indent=2) + "\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    os.chmod(path, 0o600)


def upload_video(
    youtube, args: argparse.Namespace, state: dict, state_path: Path
) -> str:
    if state.get("video_id"):
        print(f"Reusing uploaded video {state['video_id']}", flush=True)
        return state["video_id"]

    description = args.description_file.read_text().strip()
    if not args.title.strip() or len(args.title) > 100:
        raise ValueError("The title must contain 1 to 100 characters")
    if not description or len(description) > 5000:
        raise ValueError("The description must contain 1 to 5000 characters")

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": args.title.strip(),
                "description": description,
                "tags": args.tag,
                "categoryId": args.category,
                "defaultLanguage": args.language,
                "defaultAudioLanguage": args.language,
            },
            "status": {
                "privacyStatus": args.privacy,
                "selfDeclaredMadeForKids": args.made_for_kids,
                "containsSyntheticMedia": args.contains_synthetic_media,
                "embeddable": True,
            },
        },
        media_body=MediaFileUpload(
            str(args.video),
            mimetype="video/mp4",
            chunksize=8 * 1024 * 1024,
            resumable=True,
        ),
    )

    response = None
    while response is None:
        progress, response = request.next_chunk(num_retries=5)
        if progress is not None:
            print(f"Video upload: {progress.progress() * 100:.1f}%", flush=True)
    video_id = response["id"]
    state.update({"video_id": video_id, "privacy_status": args.privacy})
    save_state(state_path, state)
    return video_id


def attach_thumbnail(
    youtube,
    video_id: str,
    thumbnail: Path | None,
    state: dict,
    state_path: Path,
) -> None:
    if thumbnail is None or state.get("thumbnail_attached"):
        return
    youtube.thumbnails().set(
        videoId=video_id,
        media_body=MediaFileUpload(str(thumbnail), mimetype="image/jpeg"),
    ).execute(num_retries=5)
    state["thumbnail_attached"] = True
    save_state(state_path, state)
    print("Custom thumbnail attached", flush=True)


def attach_captions(
    youtube,
    video_id: str,
    captions: Path | None,
    language: str,
    state: dict,
    state_path: Path,
) -> str | None:
    if captions is None:
        return None
    if state.get("caption_id"):
        print(f"Reusing caption track {state['caption_id']}", flush=True)
        return state["caption_id"]
    response = (
        youtube.captions()
        .insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "language": language,
                    "name": language,
                    "isDraft": False,
                }
            },
            media_body=MediaFileUpload(
                str(captions), mimetype="application/octet-stream"
            ),
        )
        .execute(num_retries=5)
    )
    caption_id = response["id"]
    state.update(
        {
            "caption_id": caption_id,
            "caption_language": language,
            "caption_status": response.get("snippet", {}).get("status"),
        }
    )
    save_state(state_path, state)
    print(f"Caption track attached: {caption_id}", flush=True)
    return caption_id


def wait_for_processing(
    youtube, video_id: str, timeout: int, state: dict, state_path: Path
) -> dict:
    deadline = time.monotonic() + timeout
    while True:
        response = (
            youtube.videos()
            .list(part="snippet,status,processingDetails,contentDetails", id=video_id)
            .execute(num_retries=5)
        )
        items = response.get("items", [])
        if len(items) != 1:
            raise RuntimeError(
                "The uploaded video could not be retrieved; YouTube may have rejected "
                "or deleted it during processing"
            )

        video = items[0]
        result = {
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "title": video["snippet"]["title"],
            "privacy_status": video["status"]["privacyStatus"],
            "upload_status": video["status"]["uploadStatus"],
            "processing_status": video.get("processingDetails", {}).get(
                "processingStatus"
            ),
            "duration": video.get("contentDetails", {}).get("duration"),
        }
        state["video_status"] = result
        save_state(state_path, state)
        print(json.dumps(result, indent=2), flush=True)

        status = result["processing_status"]
        if status == "succeeded":
            return result
        if status in {"failed", "terminated"}:
            raise RuntimeError(f"YouTube processing {status}")
        if time.monotonic() >= deadline:
            raise TimeoutError("YouTube processing did not finish before the timeout")
        time.sleep(15)


def wait_for_caption(
    youtube,
    video_id: str,
    caption_id: str | None,
    timeout: int,
    state: dict,
    state_path: Path,
) -> dict | None:
    if caption_id is None:
        return None

    deadline = time.monotonic() + timeout
    delay = 2
    while True:
        response = (
            youtube.captions()
            .list(part="snippet", videoId=video_id)
            .execute(num_retries=5)
        )
        caption = next(
            (item for item in response.get("items", []) if item["id"] == caption_id),
            None,
        )
        if caption is not None:
            snippet = caption["snippet"]
            result = {
                "caption_id": caption_id,
                "language": snippet.get("language"),
                "status": snippet.get("status"),
                "failure_reason": snippet.get("failureReason"),
            }
            state["caption_status"] = result
            save_state(state_path, state)
            print(json.dumps(result, indent=2), flush=True)
            if result["status"] == "serving":
                return result
            if result["status"] == "failed":
                raise RuntimeError(
                    f"YouTube caption processing failed: {result['failure_reason']}"
                )

        if time.monotonic() >= deadline:
            raise TimeoutError(
                "YouTube captions did not begin serving before the timeout"
            )
        time.sleep(delay)
        delay = min(delay * 2, 15)


def main() -> None:
    args = parse_args()
    for path in (
        args.token,
        args.video,
        args.description_file,
        args.thumbnail,
        args.captions,
    ):
        require_file(path)

    credentials = Credentials.from_authorized_user_file(args.token)
    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    state_path = state_path_for(args)
    state = load_state(state_path, args.video)
    video_id = upload_video(youtube, args, state, state_path)
    print(f"Video uploaded: {video_id}", flush=True)
    attach_thumbnail(youtube, video_id, args.thumbnail, state, state_path)
    wait_for_processing(youtube, video_id, args.processing_timeout, state, state_path)
    caption_id = attach_captions(
        youtube,
        video_id,
        args.captions,
        args.caption_language,
        state,
        state_path,
    )
    wait_for_caption(
        youtube,
        video_id,
        caption_id,
        args.caption_timeout,
        state,
        state_path,
    )


if __name__ == "__main__":
    main()
