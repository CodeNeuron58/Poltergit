"""Download the two official Kokoro ONNX v1.0 assets, without overwriting files."""

import hashlib
import urllib.request
from pathlib import Path

BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"


def main():
    destination = Path("models")
    destination.mkdir(exist_ok=True)
    for name in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
        target = destination / name
        if target.exists():
            print(f"Already exists: {target}", flush=True)
            continue
        partial = target.with_suffix(target.suffix + ".partial")
        print(f"Downloading {name} from the official release...", flush=True)
        request = urllib.request.Request(BASE + name, headers={"User-Agent": "Poltergit/0.1"})
        digest = hashlib.sha256()
        with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
                digest.update(chunk)
        if partial.stat().st_size < 100_000:
            raise ValueError(f"Unexpectedly small download: {name}")
        partial.replace(target)
        print(f"Saved {target} ({target.stat().st_size:,} bytes), SHA256 {digest.hexdigest()}", flush=True)


if __name__ == "__main__":
    main()
