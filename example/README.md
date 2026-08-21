# Private upload example

This example contains a two-second, 320x180 H.264 MP4 with silent AAC audio. The video and thumbnail
are small enough to keep in Git and contain no third-party material.

Authorize your channel, then run this command from the repository root:

```sh
uv --no-config run --locked youtube-upload example/video.mp4 \
  --title "YouTube API uploader example" \
  --description-file example/description.txt \
  --tag api-upload-example \
  --thumbnail example/thumbnail.jpg \
  --captions example/captions.srt \
  --contains-synthetic-media
```

The upload is private by default. The command finishes after YouTube reports that video processing
succeeded and the caption track reached `serving`. It saves recovery state to
`example/video.mp4.youtube-upload.json`, so rerunning the command resumes the same upload.

The committed MP4 was generated with:

```sh
ffmpeg -f lavfi \
  -i 'color=c=0x17365d:s=320x180:r=24:d=2' \
  -f lavfi -i 'anullsrc=channel_layout=stereo:sample_rate=48000' \
  -vf "drawtext=text='YouTube API upload test':fontcolor=white:fontsize=18:x=(w-text_w)/2:y=(h-text_h)/2" \
  -c:v libx264 -preset veryslow -crf 40 \
  -pix_fmt yuv420p -c:a aac -b:a 16k -t 2 -movflags +faststart \
  example/video.mp4
```
