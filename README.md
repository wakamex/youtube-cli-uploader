# YouTube CLI uploader

This is a small Python client for uploading videos to an owned YouTube channel through the YouTube
Data API v3. It uses OAuth authorization, resumable uploads, and private uploads by default.

The uploader can send a title, description, tags, category, language, audience setting, synthetic
media disclosure, thumbnail, and caption track. It then checks YouTube until processing succeeds.

## Installation

Install the CLI from PyPI with uv:

```sh
uv tool install youtube-cli-uploader
```

This installs the `youtube-upload` and `youtube-authorize` commands.

## Authorization

Create an OAuth desktop client in Google Cloud for a project with the YouTube Data API v3 enabled.
Download the client JSON to:

```text
~/.config/youtube-api-uploader/client_secret.json
```

Authorize the channel:

```sh
youtube-authorize
```

Authorization prints the channel title, ID, and URL. On a headless host, forward the selected port
over SSH and run authorization with `--no-browser --port PORT`.

## Upload

```sh
youtube-upload video.mp4 \
  --title "Example upload" \
  --description-file description.txt \
  --tag example \
  --thumbnail thumbnail.jpg \
  --captions captions.srt \
  --contains-synthetic-media
```

Uploads are private unless `--privacy unlisted` or `--privacy public` is provided. API projects
that have not completed YouTube's compliance audit may be restricted to private uploads.

The uploader saves the video ID and completed steps beside the video in
`VIDEO.youtube-upload.json`. Run the same command again after a failure to resume the existing
upload instead of creating a duplicate. Use `--state PATH` to choose another state location.

## Example

[`example/`](example/) contains a ready-to-upload private test with a 5.2 KB MP4, thumbnail,
description, and captions.

## API operations

- `videos.insert` creates the video, sends its metadata, and uploads the MP4 in resumable chunks.
- `thumbnails.set` attaches the optional JPEG thumbnail.
- `videos.list` checks upload and processing status.
- `captions.insert` attaches the optional caption file after video processing succeeds.
- `captions.list` checks that the caption track reaches `serving` status.

The client requests the `youtube.upload` and `youtube.force-ssl` OAuth scopes. OAuth client secrets
and user tokens remain in the local configuration directory and are excluded from Git.

## Tests

```sh
uv --no-config run --locked python -m unittest discover -s tests
uv --no-config build --no-sources
```

## Data handling

The scripts run locally and communicate directly with Google's OAuth and YouTube API endpoints.
They do not operate a server, collect analytics, or send video data or credentials to any other
service. OAuth tokens and upload state are stored locally with owner-only permissions. Revoking the
app in the Google Account permissions page disables future access.
