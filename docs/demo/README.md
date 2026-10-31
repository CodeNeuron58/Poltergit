# Short Poltergit demo

**poltergit-demo.mp4** — 46 seconds, 1920×1080, 30 fps, H.264 video + AAC audio.

This is an edited walkthrough made from authentic saved UI screenshots and a
recorded local Kokoro voice sample. It is not a continuous screen recording.
The video explicitly labels the omitted CPU inference wait and the fictional
demo repository. UI text, model responses, and commit evidence were not altered.
The voice sample comes from another successful séance of the same line; it is
not presented as a verbatim reading of the screenshot's answer.

## Timeline

- 00:00–00:05: Poltergit introduction.
- 00:05–00:13: Actual Gemma answer for `src/client.py:13`.
- 00:13–00:20: Supporting Git commit message.
- 00:20–00:35: Recorded local Kokoro voice, with a quiet echo.
- 00:35–00:42: Ofrenda for the deleted file and function.
- 00:42–00:46: Closing card and honest-silence principle.

The soundtrack is a quiet synthesized tone; no third-party music was used.
No Tiger Data connection, Sentry dashboard, Entire integration, or hosted live
séance is claimed in the video.

## Use in the submission

Upload the MP4 to a video host you control and embed or link it in the DEV post's
Demo section. The local file is not a public video URL. `poster.jpg` is a cover
image. The video has not been uploaded or published by the build process.

## Rebuild locally

```powershell
uv run python scripts/make_demo_video.py
```

Requires the existing FFmpeg/ffprobe installation, Windows fonts, the screenshots
in `docs/screenshots/`, and the original ignored recording at
`.poltergit/audio/c122b36d95a447fbaf23bc1b925e05e0.wav`.
No additional Python dependencies are installed. Intermediate render files and
copied fonts are kept in the ignored `.poltergit/video-build/` directory.
