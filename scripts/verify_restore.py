#!/usr/bin/env python3
"""Fail-closed verifier and isolated extractor for a recipient handoff archive."""
from __future__ import annotations
import argparse, hashlib, json, pathlib, shutil, tarfile

EXPECTED_BUNDLE_SHA256 = "b7a051213c00caaa64c6274658d1edd6a9dd7511413dac5edea9a7d31bed1bae"
EXPECTED_BUNDLE_SIZE = 484042497
PROFILES = ("primary", "forge", "verifier", "eve")

def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def safe_name(name: str) -> bool:
    parts = pathlib.PurePosixPath(name).parts
    return bool(name) and not name.startswith("/") and ".." not in parts and "\\" not in name

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    parser.add_argument("--fixture-root", required=True)
    args = parser.parse_args()
    archive, fixture = pathlib.Path(args.archive), pathlib.Path(args.fixture_root)
    if not archive.is_file(): raise SystemExit("archive does not exist")
    if fixture.exists(): shutil.rmtree(fixture)
    fixture.mkdir(parents=True)
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers(); names = [m.name for m in members]
        if len(names) != len(set(names)) or any(not safe_name(n) or not (m.isfile() or m.isdir()) for n, m in zip(names, members)):
            raise SystemExit("archive contains unsafe or duplicate members")
        prefix = "hermes-client-handoff/"
        if any(not n.startswith(prefix) for n in names): raise SystemExit("archive root is invalid")
        tar.extractall(fixture, filter="data")
    package = fixture / "hermes-client-handoff"
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    if tuple(sorted(manifest["profiles"])) != tuple(sorted(PROFILES)): raise SystemExit("profile inventory is invalid")
    for entry in manifest["files"]:
        target = package / entry["path"]
        if not target.is_file() or target.stat().st_size != entry["size"] or sha256(target) != entry["sha256"]:
            raise SystemExit(f"manifest mismatch: {entry['path']}")
    bundle = package / "bundle" / "hermes-native-pipeline-0.21.2-full.bundle"
    if bundle.stat().st_size != EXPECTED_BUNDLE_SIZE or sha256(bundle) != EXPECTED_BUNDLE_SHA256: raise SystemExit("bundle provenance mismatch")
    print(json.dumps({"restore": "passed", "fixture_root": str(fixture), "profiles": list(PROFILES), "archive_sha256": sha256(archive)}, sort_keys=True))
    return 0
if __name__ == "__main__": raise SystemExit(main())
