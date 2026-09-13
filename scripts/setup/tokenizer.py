"""Plan or fetch the pinned public tokenizer vocabulary, never a model request."""

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
URL = "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken"
SHA256 = "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7"
CACHE = ROOT / ".runtime/automanual-tokenizer"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args()
    destination = CACHE / hashlib.sha1(URL.encode()).hexdigest()
    if args.fetch:
        if destination.exists():
            data = destination.read_bytes()
        else:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(URL, timeout=30) as response:
                data = response.read(4 * 1024 * 1024)
        if hashlib.sha256(data).hexdigest() != SHA256:
            raise RuntimeError("tokenizer_checksum_mismatch")
        CACHE.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            with destination.open("xb") as stream:
                stream.write(data)
    print(json.dumps({"url": URL, "sha256": SHA256, "mode": "fetch" if args.fetch else "plan"}))


if __name__ == "__main__":
    main()
