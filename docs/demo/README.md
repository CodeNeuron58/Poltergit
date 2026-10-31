# Short Poltergit demo

**poltergit-demo-narrated.mp4** — the revised narrated walkthrough, 1920×1080, 30 fps,
H.264 video + AAC audio. Exact timings are recorded in `timeline.json`.
Use this version for submission. `poltergit-demo.mp4` preserves the original
46-second version with the voice sample and atmosphere, for comparison.

This is an edited walkthrough made from authentic saved UI screenshots and a
clean local Kokoro AI voiceover throughout. It is not a continuous screen recording.
The video explicitly labels the omitted CPU inference wait and the fictional
demo repository. UI text, model responses, and commit evidence were not altered.
The voice chapter reads the actual answer shown in the screenshot. Narration is
generated directly through Kokoro without the application's echo effect.

## Chapters

- Poltergit introduction.
- Actual Gemma answer for `src/client.py:13`.
- Supporting Git commit message.
- A clean Kokoro reading of the displayed answer.
- Ofrenda for the deleted file and function.
- Closing card and honest-silence principle.

There is no background hum, music, echo, or reverb in the revised video.
The full AI narration script is saved in `narration.txt`. Scene lengths adjust
to fit the speech naturally without cutting words or speeding up the audio.
No Tiger Data connection, Sentry dashboard, Entire integration, or hosted live
séance is claimed in the video.

## Use in the submission

Upload the MP4 to a video host you control and embed or link it in the DEV post's
Demo section. The local file is not a public video URL. `poster.jpg` is a cover
image. The video has not been uploaded or published by the build process.

## Rebuild locally

```powershell
uv run --extra voice python scripts/make_demo_video.py
```

Requires the existing FFmpeg/ffprobe installation, Windows fonts, the screenshots
in `docs/screenshots/`, voice extras, and the local Kokoro model/voices configured
in `.env`. No additional Python dependencies were installed for this revision.
Narration is cached by text and voice settings. Intermediate render files,
voice WAVs, and copied fonts are kept in the ignored `.poltergit/video-build/`
directory. The app's own ghost-voice effect remains unchanged.
