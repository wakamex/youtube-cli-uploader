#!/usr/bin/env bash
set -euo pipefail

demo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
fake_state=${YOUTUBE_DEMO_FAKE_STATE:?YOUTUBE_DEMO_FAKE_STATE must be set}
token="$demo_root/demo/fixtures/fake-token.json"
upload_state="$PWD/upload-state.json"

cleanup() {
    if python "$demo_root/demo/support/assert_present.py" "$fake_state" >/dev/null 2>&1; then
        youtube-delete demo-video-id --token "$token" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT

show() {
    printf '$ %s\n' "$1"
    shift
    "$@"
    sleep 0.2
}

show "youtube-upload --version" youtube-upload --version
show "youtube-upload video.mp4 with metadata, thumbnail, and captions" \
    youtube-upload "$demo_root/example/video.mp4" \
        --title "CI demo upload" \
        --description-file "$demo_root/example/description.txt" \
        --tag ci-demo \
        --thumbnail "$demo_root/example/thumbnail.jpg" \
        --captions "$demo_root/example/captions.srt" \
        --contains-synthetic-media \
        --token "$token" \
        --state "$upload_state"
show "youtube-delete demo-video-id" \
    youtube-delete demo-video-id --token "$token"
show "verify the uploaded video was deleted" \
    python "$demo_root/demo/support/assert_deleted.py" "$fake_state"
