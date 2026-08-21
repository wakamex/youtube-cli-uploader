import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock, patch

from youtube_cli_uploader import delete, upload


class UploadRequest:
    def next_chunk(self, **kwargs):
        return None, {"id": "video-id"}


class Videos:
    def __init__(self):
        self.insert_calls = 0

    def insert(self, **kwargs):
        self.insert_calls += 1
        return UploadRequest()


class FailingCaptions:
    def insert(self, **kwargs):
        raise RuntimeError("caption upload failed")


class YouTube:
    def __init__(self):
        self.video_resource = Videos()

    def videos(self):
        return self.video_resource

    def captions(self):
        return FailingCaptions()


class UploadTests(unittest.TestCase):
    def test_processing_wait_is_explained_between_status_results(self):
        processing = {
            "snippet": {"title": "Example", "channelId": "channel-id"},
            "status": {"privacyStatus": "private", "uploadStatus": "uploaded"},
            "processingDetails": {"processingStatus": "processing"},
            "contentDetails": {"duration": "P0D"},
        }
        succeeded = {
            **processing,
            "status": {"privacyStatus": "private", "uploadStatus": "processed"},
            "processingDetails": {"processingStatus": "succeeded"},
            "contentDetails": {"duration": "PT2S"},
        }
        youtube = Mock()
        youtube.videos.return_value.list.return_value.execute.side_effect = [
            {"items": [processing]},
            {"items": [succeeded]},
        ]

        with (
            tempfile.TemporaryDirectory() as directory,
            patch("builtins.print") as print_mock,
            patch.object(upload.time, "sleep") as sleep_mock,
        ):
            upload.wait_for_processing(
                youtube, "video-id", 60, {}, Path(directory) / "state.json"
            )

        print_mock.assert_any_call(
            "Waiting for YouTube processing to finish...", end="", flush=True
        )
        print_mock.assert_any_call(" done!", flush=True)
        sleep_mock.assert_called_once_with(15)

    def test_delete_video_waits_for_api_success(self):
        request = Mock()
        youtube = Mock()
        youtube.videos.return_value.delete.return_value = request

        delete.delete_video(youtube, "video-id")

        youtube.videos.return_value.delete.assert_called_once_with(id="video-id")
        request.execute.assert_called_once_with(num_retries=5)

    def test_caption_failure_resumes_without_uploading_another_video(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video = root / "video.mp4"
            description = root / "description.txt"
            captions = root / "captions.srt"
            state_path = root / "state.json"
            video.write_bytes(b"video")
            description.write_text("Description")
            captions.write_text("Captions")
            args = Namespace(
                video=video,
                title="Example",
                description_file=description,
                tag=[],
                category="28",
                language="en",
                privacy="private",
                made_for_kids=False,
                contains_synthetic_media=False,
            )
            youtube = YouTube()
            state = upload.load_state(state_path, video)

            video_id = upload.upload_video(youtube, args, state, state_path)
            with self.assertRaisesRegex(RuntimeError, "caption upload failed"):
                upload.attach_captions(
                    youtube, video_id, captions, "en", state, state_path
                )

            resumed_state = upload.load_state(state_path, video)
            resumed_id = upload.upload_video(youtube, args, resumed_state, state_path)

            self.assertEqual(resumed_id, video_id)
            self.assertEqual(youtube.video_resource.insert_calls, 1)

    def test_processing_finishes_before_captions_are_attached(self):
        args = Namespace(
            token=Path("token.json"),
            video=Path("video.mp4"),
            description_file=Path("description.txt"),
            thumbnail=Path("thumbnail.jpg"),
            captions=Path("captions.srt"),
            caption_language="en",
            state=Path("state.json"),
            processing_timeout=60,
            caption_timeout=60,
        )
        events = []

        def record_upload(*unused):
            events.append("upload")
            return "video-id"

        def record_caption(*unused):
            events.append("captions")
            return "caption-id"

        with (
            patch.object(upload, "parse_args", return_value=args),
            patch.object(upload, "require_file"),
            patch.object(upload.Credentials, "from_authorized_user_file"),
            patch.object(upload, "build", return_value=object()),
            patch.object(upload, "load_state", return_value={}),
            patch.object(upload, "upload_video", side_effect=record_upload),
            patch.object(
                upload,
                "attach_thumbnail",
                side_effect=lambda *unused: events.append("thumbnail"),
            ),
            patch.object(
                upload,
                "wait_for_processing",
                side_effect=lambda *unused: events.append("processing"),
            ),
            patch.object(upload, "attach_captions", side_effect=record_caption),
            patch.object(
                upload,
                "wait_for_caption",
                side_effect=lambda *unused: events.append("caption_serving"),
            ),
        ):
            upload.main()

        self.assertEqual(
            events,
            ["upload", "thumbnail", "processing", "captions", "caption_serving"],
        )


if __name__ == "__main__":
    unittest.main()
