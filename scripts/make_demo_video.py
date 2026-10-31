"""Render the short demo from authentic UI captures and clean Kokoro narration.

Uses the already-installed local voice model. Requires ffmpeg/ffprobe and voice extras.
Run from the project root: uv run --extra voice python scripts/make_demo_video.py
"""

import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / ".poltergit" / "video-build"
OUTPUT = ROOT / "docs" / "demo"
FPS = 30
WIDTH, HEIGHT = 1920, 1080
INK = "0x141714"
PAPER = "0xe9e4d5"
GOLD = "0xc7ad77"
MUTED = "0xadb7a2"

# Crops are framing only. No UI values or model responses are altered.
SCENES = [
    dict(duration=5, image="01-seance-home.png", crop=(62, 116, 1140, 405),
         box=(100, 215, 1720, 612), chapter="POLTERGIT", title="A séance for your Git history.",
         caption="Ask a line why it exists. Let the history speak.", note="Recorded local demo · fictional repository with real Git history",
         narration="Some code never rests. Poltergit asks a line why it exists."),
    dict(duration=8, image="08-seance-gemma.png", crop=(69, 38, 1128, 610),
         box=(300, 210, 1320, 714), chapter="01 / ASK THE CODE", title="Why am I waiting three seconds?",
         caption="Gemma 4 answers in the line’s own voice, with a citation.", note="Actual recorded model result · CPU inference wait omitted",
         narration="This three-second delay answers through Gemma, running locally. It speaks as the code, with a citation."),
    dict(duration=7, image="03-evidence-cards.png", crop=(70, 285, 563, 240),
         box=(260, 235, 1400, 597), chapter="02 / FOLLOW THE EVIDENCE", title="Every ghost brings receipts.",
         caption="The commit explains the gateway’s two-second reservation.", note="Original commit message · supporting quotations are checked against the source",
         narration="The original commit explains it: the gateway reserves closed sessions for two seconds. Every ghost brings receipts."),
    dict(duration=12, image="08-seance-gemma.png", crop=(665, 183, 530, 465),
         box=(790, 190, 815, 715), chapter="03 / HEAR THE SPIRIT", title="The code has a voice.",
         caption="Kokoro gives the code a voice, entirely locally.", note="Clean AI narration · reading the actual answer shown here", voice=True,
         narration="Kokoro gives the code a voice. My existence is tied to preventing a reconnect storm, as a three-second delay gives that reservation time to expire."),
    dict(duration=7, image="05-ofrenda.png", crop=(69, 403, 767, 380),
         box=(280, 220, 1360, 674), chapter="04 / HONOR THE PAST", title="Gone from the tree. Still part of the story.",
         caption="Deleted code gets an ofrenda: its lifetime and removal record.", note="A standalone memorial site, ready to publish on GitHub Pages",
         narration="The ofrenda remembers deleted code: how long it served, and the commit that retired it."),
    dict(duration=4, chapter="POLTERGIT", title="Some code never rests.",
         caption="Local Gemma. Real Git history. Sources you can inspect.",
         note="When evidence is missing: “The record is silent.”", end=True,
         narration="And when history has no answer, the record is silent."),
]


def run(args):
    subprocess.run(args, cwd=ROOT, check=True)


def rel(path):
    return Path(path).relative_to(ROOT).as_posix()


def text_filter(index, key, value, size, y, *, color=PAPER, font="sans", x=None):
    path = BUILD / f"{index}-{key}.txt"
    path.write_text(value, encoding="utf-8")
    return (f"drawtext=fontfile='{rel(BUILD / (font + '.ttf'))}':"
            f"textfile='{rel(path)}':fontcolor={color}:fontsize={size}:"
            f"x={x if x is not None else '(w-text_w)/2'}:y={y}")


def make_narration():
    """Generate dry speech directly; never apply the app's ghost echo or a hum."""
    import numpy as np
    import soundfile as sf
    from poltergit.config import Settings
    from poltergit.voice import engine

    settings = Settings()
    synthesizer = None
    combined = []
    rate = 24000
    for index, scene in enumerate(SCENES):
        signature = hashlib.sha256(("af_heart:1.06:" + scene["narration"]).encode()).hexdigest()[:12]
        cache = BUILD / f"narration-{index}-{signature}.wav"
        if cache.exists():
            samples, rate = sf.read(str(cache), dtype="float32")
        else:
            if synthesizer is None:
                synthesizer = engine(str(settings.kokoro_model), str(settings.kokoro_voices))
            print(f"Synthesizing clean narration {index + 1}/{len(SCENES)}", flush=True)
            samples, rate = synthesizer.create(scene["narration"], voice="af_heart", speed=1.06, lang="en-us")
            samples = np.asarray(samples, dtype=np.float32)
            # Trim long synthesis padding, keeping 50 ms around speech.
            active = np.flatnonzero(np.abs(samples) > 0.003)
            if not len(active):
                raise ValueError("The local voice model returned silent audio.")
            margin = int(0.05 * rate)
            samples = samples[max(0, active[0] - margin):min(len(samples), active[-1] + margin)]
            sf.write(str(cache), samples, rate)
        lead = 0.25
        duration = max(scene["duration"], math.ceil((len(samples) / rate + lead + 0.35) * FPS) / FPS)
        scene["duration"] = duration
        scene["speech_seconds"] = round(len(samples) / rate, 3)
        padded = np.zeros(round(duration * rate), dtype=np.float32)
        offset = int(lead * rate)
        padded[offset:offset + len(samples)] = samples
        combined.append(padded)
        print(f"Narration {index + 1}: {len(samples) / rate:.1f}s speech, {duration:.1f}s scene", flush=True)
    destination = BUILD / "clean-narration.wav"
    sf.write(str(destination), np.concatenate(combined), rate)
    return destination


def main():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("Install FFmpeg before rendering the demo.")
    BUILD.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    narration = make_narration()
    font_sources = {"sans": "segoeui.ttf", "serif": "georgia.ttf", "italic": "georgiai.ttf", "mono": "consola.ttf"}
    for name, source in font_sources.items():
        path = Path("C:/Windows/Fonts") / source
        if not path.is_file():
            raise SystemExit(f"Font unavailable: {path}. Adapt font_sources for your OS.")
        shutil.copyfile(path, BUILD / f"{name}.ttf")

    clips = []
    for index, scene in enumerate(SCENES):
        duration = scene["duration"]
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                   "-i", f"color=c={INK}:s={WIDTH}x{HEIGHT}:r={FPS}:d={duration}"]
        filters = []
        if scene.get("image"):
            image = ROOT / "docs/screenshots" / scene["image"]
            command += ["-loop", "1", "-framerate", str(FPS), "-i", str(image)]
            cx, cy, cw, ch = scene["crop"]
            x, y, w, h = scene["box"]
            filters += [f"[1:v]crop={cw}:{ch}:{cx}:{cy},scale={w}:{h}:flags=lanczos,setsar=1[picture]",
                        f"[0:v][picture]overlay={x}:{y}:shortest=1[composed]"]
            base = "[composed]"
        else:
            base = "[0:v]"

        draw = ["drawbox=x=80:y=111:w=1760:h=1:color=0x343c30:t=fill",
                text_filter(index, "chapter", scene["chapter"], 24, 49, color=GOLD, font="mono", x=82),
                text_filter(index, "counter", f"{index + 1:02d} / 06", 21, 52, color=MUTED, font="mono", x=1720)]
        if scene.get("end"):
            draw += [text_filter(index, "title", scene["title"], 104, 350, font="italic", color=GOLD),
                     text_filter(index, "statement", "A séance for your Git history.", 48, 500, font="serif")]
        elif scene.get("voice"):
            draw += [text_filter(index, "title", "The code", 70, 360, font="serif", x=140),
                     text_filter(index, "title2", "has a voice.", 70, 450, font="italic", color=GOLD, x=140),
                     text_filter(index, "voice-tag", "KOKORO / LOCAL AUDIO", 23, 560, color=MUTED, font="mono", x=145)]
        else:
            draw += [text_filter(index, "title", scene["title"], 43, 140, font="serif")]
        draw += ["drawbox=x=80:y=946:w=1760:h=1:color=0x343c30:t=fill",
                 text_filter(index, "caption", scene["caption"], 34, 966),
                 text_filter(index, "note", scene["note"], 21, 1024, color=MUTED),
                 "fade=t=in:st=0:d=0.25", f"fade=t=out:st={duration - 0.25}:d=0.25", "format=yuv420p"]
        filters += [base + ",".join(draw) + "[video]"]
        clip = BUILD / f"scene-{index}.mp4"
        command += ["-filter_complex", ";".join(filters), "-map", "[video]", "-t", str(duration),
                    "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-threads", "2",
                    "-movflags", "+faststart", str(clip)]
        print(f"Rendering scene {index + 1}/{len(SCENES)} ({duration}s)", flush=True)
        run(command)
        clips.append(clip)

    concat = BUILD / "clips.txt"
    concat.write_text("\n".join(f"file '{path.name}'" for path in clips), encoding="utf-8")
    picture = BUILD / "picture.mp4"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
         "-i", str(concat), "-c", "copy", str(picture)])

    total = sum(s["duration"] for s in SCENES)
    target = OUTPUT / "poltergit-demo-narrated.mp4"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(picture),
         "-i", str(narration), "-map", "0:v:0", "-map", "1:a:0", "-t", str(total),
         "-af", "highpass=f=65,loudnorm=I=-16:TP=-1.5:LRA=7",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
         "-movflags", "+faststart", "-metadata", "title=Poltergit — a séance for your Git history",
         "-metadata", "comment=Authentic local screenshots with clean local Kokoro AI narration throughout. No echo or background music. Inference wait omitted.", str(target)])

    timeline = []
    start = 0
    for scene in SCENES:
        timeline.append({"start_seconds": start, "end_seconds": start + scene["duration"],
                         "chapter": scene["chapter"], "caption": scene["caption"],
                         "narration": scene["narration"], "speech_seconds": scene["speech_seconds"],
                         "source": scene.get("image", "Original title card")})
        start += scene["duration"]
    (OUTPUT / "timeline.json").write_text(json.dumps(timeline, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUTPUT / "narration.txt").write_text("\n\n".join(s["narration"] for s in SCENES) + "\n", encoding="utf-8")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", "2", "-i", str(target),
         "-frames:v", "1", str(OUTPUT / "poster.jpg")])
    print(f"Saved {target} ({total}s, {target.stat().st_size / 1_000_000:.1f} MB)", flush=True)


if __name__ == "__main__":
    main()
