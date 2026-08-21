#!/usr/bin/env bash
set -euo pipefail

repository_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
token=${1:-$HOME/.config/youtube-api-uploader/token.json}
artifact_directory=${2:-$repository_root/artifacts/live-demo}

if [[ ! -f "$token" ]]; then
    echo "OAuth token not found: $token" >&2
    exit 1
fi
if ! asciinema --version | grep -Eq '^asciinema 3\.'; then
    echo "asciinema 3.x is required" >&2
    exit 1
fi

temporary_root=$(mktemp -d)
cleanup() {
    rm -rf -- "$temporary_root"
}
trap cleanup EXIT

mkdir -p \
    "$artifact_directory" \
    "$temporary_root/dist" \
    "$temporary_root/work/example"
artifact_directory=$(cd "$artifact_directory" && pwd)
cp "$token" "$temporary_root/work/token.json"
chmod 600 "$temporary_root/work/token.json"
cp "$repository_root"/example/* "$temporary_root/work/example/"

cd "$repository_root"
uv --no-config run --locked python -m unittest discover -s tests
uv --no-config export \
    --quiet \
    --locked \
    --no-dev \
    --no-emit-project \
    --output-file "$temporary_root/requirements.txt"
uv --no-config build --no-sources --out-dir "$temporary_root/dist"
uv --no-config venv "$temporary_root/venv"
uv --no-config pip sync \
    --python "$temporary_root/venv/bin/python" \
    "$temporary_root/requirements.txt"
uv --no-config pip install \
    --python "$temporary_root/venv/bin/python" \
    --no-deps \
    "$temporary_root"/dist/*.whl

export PATH="$temporary_root/venv/bin:$PATH"
export LC_ALL=C.UTF-8
export TZ=UTC
export TERM=xterm-256color
export ASCIINEMA_CONFIG_HOME="$temporary_root/asciinema-config"

cd "$temporary_root/work"
asciinema rec "$artifact_directory/live-demo.cast" \
    --command "$repository_root/demo/live-demo.sh" \
    --headless \
    --window-size 100x30 \
    --capture-env TERM,LC_ALL,TZ \
    --return \
    --overwrite
python "$repository_root/demo/shorten_cast.py" \
    "$artifact_directory/live-demo.cast" \
    --max-idle 2

asciinema convert \
    --overwrite \
    "$artifact_directory/live-demo.cast" \
    "$artifact_directory/live-demo.txt"
wheels=("$temporary_root"/dist/*.whl)
if [[ ${#wheels[@]} -ne 1 ]]; then
    echo "Expected exactly one wheel, found ${#wheels[@]}" >&2
    exit 1
fi
wheel_name=$(basename "${wheels[0]}")
cp "${wheels[0]}" "$artifact_directory/$wheel_name"
cd "$artifact_directory"
sha256sum "$wheel_name" live-demo.cast live-demo.txt > SHA256SUMS

printf 'Live demo saved to %s\n' "$artifact_directory"
