from functools import lru_cache
from pathlib import Path

from .config import Settings
from .telemetry import Trace


@lru_cache(maxsize=1)
def engine(model: str, voices: str):
    try:
        from kokoro_onnx import Kokoro
    except ImportError as exc:
        raise ValueError("Install voice support with uv sync --extra voice.") from exc
    return Kokoro(model, voices)


def narrate(text: str, settings: Settings, identifier: str) -> Path:
    if not settings.kokoro_model.is_file() or not settings.kokoro_voices.is_file():
        raise ValueError("Kokoro model files are missing. See docs/SETUP.md for the free local voice setup.")
    with Trace(settings, "voice") as trace:
        with trace.step("Speak with Kokoro", "voice.synthesize"):
            try:
                import numpy as np
                import soundfile as sf
                kokoro = engine(str(settings.kokoro_model), str(settings.kokoro_voices))
                samples, rate = kokoro.create(text[:5000], voice=settings.voice, speed=0.87, lang="en-us")
                # Quiet delayed reflections give the voice its séance-room character.
                delay = int(rate * 0.12)
                ghost = np.pad(samples, (0, delay * 3)).astype(np.float32)
                for bounce, gain in ((1, 0.19), (2, 0.09), (3, 0.04)):
                    start = delay * bounce
                    ghost[start:start + len(samples)] += samples * gain
                ghost /= max(1.0, float(np.max(np.abs(ghost))))
                destination = settings.state_dir / "audio" / f"{identifier}.wav"
                destination.parent.mkdir(parents=True, exist_ok=True)
                sf.write(str(destination), ghost, rate)
            except (ImportError, OSError, RuntimeError) as exc:
                raise ValueError("Kokoro could not synthesize audio. Check the voice extras and model files.") from exc
    return destination
