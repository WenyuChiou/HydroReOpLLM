"""Verify the F.E. Walter manuscript model and archived system prompts locally."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import urlopen


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(manifest, blobs, lock):
    actual = digest(manifest)
    if actual != lock["manifest_sha256"]:
        raise ValueError(f"Model manifest mismatch: {actual}")
    data = json.loads(manifest.read_bytes())
    layers = [data["config"], *data["layers"]]
    for layer in layers:
        algorithm, expected = layer["digest"].split(":")
        if algorithm != "sha256" or len(expected) != 64:
            raise ValueError("Invalid digest in the pinned manifest")
        path = blobs / ("sha256-" + expected)
        if path.stat().st_size != layer["size"] or digest(path) != expected:
            raise ValueError(f"Blob integrity mismatch: {path.name}")
    return len(layers)


def verify_server(port, lock):
    if not 1 <= port <= 65535:
        raise ValueError("Invalid port")
    def get(endpoint):
        with urlopen(f"http://127.0.0.1:{port}/api/{endpoint}", timeout=5) as reply:
            return json.load(reply)
    version = get("version")["version"]
    if version != lock["ollama_version"]:
        raise ValueError(f"Ollama version mismatch: {version}")
    rows = [m for m in get("tags")["models"] if m["name"] == lock["model_tag"]]
    if len(rows) != 1 or rows[0]["digest"] != lock["manifest_sha256"]:
        raise ValueError("The serving model tag does not resolve to the paper digest")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Raw Ollama manifest from archive or local store")
    parser.add_argument("blobs", type=Path, help="Ollama blobs directory")
    parser.add_argument("--server-port", type=int, help="Also check running localhost Ollama version and tag")
    parser.add_argument("--rules", type=Path, help="Also check an author-supplied copy of the paper DKP")
    args = parser.parse_args()
    folder = Path(__file__).resolve().parent
    lock = json.loads((folder / "paper-model-lock.json").read_bytes())
    count = verify(args.manifest, args.blobs, lock)
    for arm in lock["prompt_comparison"]:
        if digest(folder / arm["system_prompt_file"]) != arm["system_prompt_sha256"]:
            raise ValueError(f"Archived system prompt mismatch for {arm['agent']}")
    if args.rules is not None:
        expected, = [arm["operating_rules_sha256"] for arm in lock["prompt_comparison"]
                     if arm["operating_rules_sha256"]]
        if digest(args.rules) != expected:
            raise ValueError("Operating knowledge file differs from the manuscript DKP")
    if args.server_port is not None:
        verify_server(args.server_port, lock)
    print(f"PASS: paper manifest, {count} blobs and both system prompts verified.")
    if args.rules is not None:
        print("PASS: operating knowledge file matches the manuscript DKP.")
    if args.server_port is not None:
        print(f"PASS: local server identity matches Ollama {lock['ollama_version']} and the paper model.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as err:
        print(f"FAIL: {err}", file=sys.stderr)
        sys.exit(1)
