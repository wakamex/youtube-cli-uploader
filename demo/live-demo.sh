#!/usr/bin/env bash
set -euo pipefail

token="$PWD/token.json"
state="$PWD/upload-state.json"
deleted=false

video_id() {
    python - "$state" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if path.exists():
    print(json.loads(path.read_text()).get("video_id", ""))
PY
}

cleanup() {
    uploaded_video_id=$(video_id)
    if [[ "$deleted" == false && -n "$uploaded_video_id" ]]; then
        youtube-delete "$uploaded_video_id" --token "$token" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT

show() {
    printf '$ %s\n' "$1"
    shift
    "$@"
    sleep 0.5
}

show "youtube-upload --version" youtube-upload --version
printf '%s\n' '$ youtube-upload example/video.mp4 \'
printf '%s\n' '    --title "YouTube CLI uploader verification demo" \'
printf '%s\n' '    --description-file example/description.txt \'
printf '%s\n' '    --tag api-verification-demo \'
printf '%s\n' '    --thumbnail example/thumbnail.jpg \'
printf '%s\n' '    --captions example/captions.srt \'
printf '%s\n' '    --token token.json \'
printf '%s\n' '    --state upload-state.json'
youtube-upload example/video.mp4 \
    --title "YouTube CLI uploader verification demo" \
    --description-file example/description.txt \
    --tag api-verification-demo \
    --thumbnail example/thumbnail.jpg \
    --captions example/captions.srt \
    --token token.json \
    --state upload-state.json
sleep 0.5

uploaded_video_id=$(video_id)
if [[ -z "$uploaded_video_id" ]]; then
    echo "The upload did not save a video ID" >&2
    exit 1
fi

show "youtube-delete $uploaded_video_id --token token.json" \
    youtube-delete "$uploaded_video_id" --token "$token"
deleted=true
