"""Install the study model's verified public Ollama blobs into a dedicated store."""

import argparse
from hashlib import file_digest, sha256
import json
import os
from pathlib import Path
from shutil import copyfileobj
from tempfile import NamedTemporaryFile
from urllib.request import urlopen


MODEL = "gemma4:12b"
VERSION = "0.40.6"
DIGEST = "4eb23ef187e2c5462566d6a1d3bbbc2f1346d0b4327cbb66d58fffbcc9b2b05c"
MODEL_ROOT = Path("manifests/registry.ollama.ai/library/gemma4/12b")
REGISTRY = "https://registry.ollama.ai/v2/library/gemma4/blobs/"


def verify_serving(base_url):
    with urlopen(f"{base_url}/api/version", timeout=10) as response:
        version = json.load(response)["version"]
    with urlopen(f"{base_url}/api/tags", timeout=10) as response:
        models = json.load(response)["models"]
    if version != VERSION or not any(
        model["name"] == MODEL and model["digest"].removeprefix("sha256:") == DIGEST for model in models
    ):
        raise ValueError(f"requires Ollama {VERSION} serving {MODEL} with manifest {DIGEST}")


def _matches(path, size, digest):
    if not path.is_file() or path.stat().st_size != size:
        return False
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest() == digest


def restore(output, source_models=None):
    manifest = Path(__file__).with_name("ollama-manifest.json").read_bytes()
    if sha256(manifest).hexdigest() != DIGEST:
        raise ValueError("study model manifest failed SHA-256 verification")
    data = json.loads(manifest)
    manifest_path = output / MODEL_ROOT
    if manifest_path.exists() and manifest_path.read_bytes() != manifest:
        raise FileExistsError(f"a different {MODEL} already exists in {output}; select a dedicated study directory")
    blobs = output / "blobs"
    blobs.mkdir(parents=True, exist_ok=True)
    for blob in (data["config"], *data["layers"]):
        digest = blob["digest"].removeprefix("sha256:")
        name = f"sha256-{digest}"
        target = blobs / name
        if _matches(target, blob["size"], digest):
            continue
        if target.exists():
            raise ValueError(f"existing blob has the wrong SHA-256 or size: {target}")
        source = ((source_models / "blobs" / name).open("rb") if source_models else
                  urlopen(REGISTRY + blob["digest"], timeout=120))
        with source, NamedTemporaryFile(dir=blobs, delete=False) as temporary:
            path = Path(temporary.name)
            try:
                copyfileobj(source, temporary, length=1024 * 1024)
                temporary.close()
                if not _matches(path, blob["size"], digest):
                    raise ValueError(f"downloaded blob failed verification: {blob['digest']}")
                os.replace(path, target)
            finally:
                path.unlink(missing_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if not manifest_path.exists():
        with manifest_path.open("xb") as stream:
            stream.write(manifest)
    print(f"Verified {MODEL} manifest {DIGEST} in {output.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Dedicated Ollama model directory")
    parser.add_argument("--from-models", type=Path, help="Copy the same verified blobs from an existing model store")
    args = parser.parse_args()
    restore(args.output, args.from_models)
