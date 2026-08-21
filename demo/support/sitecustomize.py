"""Install a deterministic YouTube API fixture for the recorded demo."""

import json
import os
from pathlib import Path


def _read_state(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {"videos": {}, "captions": {}}


def _write_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, sort_keys=True))


class _Request:
    def __init__(self, response=None, callback=None):
        self.response = response
        self.callback = callback

    def execute(self, **unused):
        if self.callback is not None:
            self.callback()
        return self.response


class _UploadRequest(_Request):
    def next_chunk(self, **unused):
        self.execute()
        return None, self.response


class _Videos:
    def __init__(self, path: Path):
        self.path = path

    def insert(self, body, **unused):
        video_id = "demo-video-id"

        def save():
            state = _read_state(self.path)
            state["videos"][video_id] = {
                "snippet": {
                    **body["snippet"],
                    "channelId": "demo-channel-id",
                },
                "status": {
                    "privacyStatus": body["status"]["privacyStatus"],
                    "uploadStatus": "processed",
                },
                "processingDetails": {"processingStatus": "succeeded"},
                "contentDetails": {"duration": "PT2S"},
            }
            _write_state(self.path, state)

        return _UploadRequest({"id": video_id}, save)

    def list(self, id, **unused):
        state = _read_state(self.path)
        video = state["videos"].get(id)
        return _Request({"items": [video] if video else []})

    def delete(self, id):
        def remove():
            state = _read_state(self.path)
            if id not in state["videos"]:
                raise RuntimeError(f"Video does not exist: {id}")
            del state["videos"][id]
            state["captions"].pop(id, None)
            _write_state(self.path, state)

        return _Request(callback=remove)


class _Thumbnails:
    def set(self, **unused):
        return _Request({})


class _Captions:
    def __init__(self, path: Path):
        self.path = path

    def insert(self, body, **unused):
        video_id = body["snippet"]["videoId"]
        caption = {
            "id": "demo-caption-id",
            "snippet": {
                "language": body["snippet"]["language"],
                "status": "serving",
            },
        }

        def save():
            state = _read_state(self.path)
            state["captions"][video_id] = caption
            _write_state(self.path, state)

        return _Request(caption, save)

    def list(self, videoId, **unused):
        caption = _read_state(self.path)["captions"].get(videoId)
        return _Request({"items": [caption] if caption else []})


class _YouTube:
    def __init__(self, path: Path):
        self.path = path

    def videos(self):
        return _Videos(self.path)

    def thumbnails(self):
        return _Thumbnails()

    def captions(self):
        return _Captions(self.path)


state_value = os.environ.get("YOUTUBE_DEMO_FAKE_STATE")
if state_value:
    try:
        from google.oauth2.credentials import Credentials
        import googleapiclient.discovery
    except ModuleNotFoundError:
        pass
    else:
        state_path = Path(state_value)
        Credentials.from_authorized_user_file = classmethod(lambda cls, path: object())
        googleapiclient.discovery.build = lambda *args, **kwargs: _YouTube(state_path)
