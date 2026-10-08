#!/usr/bin/env python3
"""Build a deterministic, privacy-clean Hermes recipient handoff archive."""
from __future__ import annotations
import argparse, gzip, hashlib, json, os, pathlib, shutil, stat, tarfile

EXPECTED_BUNDLE_SHA256 = "b7a051213c00caaa64c6274658d1edd6a9dd7511413dac5edea9a7d31bed1bae"
EXPECTED_BUNDLE_SIZE = 484042497
EXPECTED_HEAD = "7d01f6ddf39b1e07647edd9fe3004c4a215fd314"
EXPECTED_BASE = "c6f87deb2c38d75518c793790f1cc9afa37f0695"
PROFILES = ("primary", "forge", "verifier", "eve")
ROOT = pathlib.Path(__file__).resolve().parents[1]

def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def safe_files(root: pathlib.Path):
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        info = os.lstat(path)
        if stat.S_ISLNK(info.st_mode) or not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            raise ValueError(f"unsafe package source member: {relative}")
        if path.is_file():
            yield path, relative

def add_file(tar: tarfile.TarFile, source: pathlib.Path, name: str) -> None:
    info = tarfile.TarInfo(name)
    info.size = source.stat().st_size
    info.mode = 0o644
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    info.mtime = 0
    with source.open("rb") as handle:
        tar.addfile(info, handle)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-source", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    bundle, output = pathlib.Path(args.bundle_source), pathlib.Path(args.output_dir)
    if not bundle.is_file() or bundle.stat().st_size != EXPECTED_BUNDLE_SIZE or sha256(bundle) != EXPECTED_BUNDLE_SHA256:
        raise SystemExit("immutable Hermes source bundle provenance check failed")
    package = ROOT / "runtime-bundle"
    if not package.is_dir():
        raise SystemExit("missing package template")
    profile_root = package / "profiles"
    if tuple(sorted(p.name for p in profile_root.iterdir() if p.is_dir())) != tuple(sorted(PROFILES)):
        raise SystemExit("package profile inventory must be exactly primary, forge, verifier, eve")
    output.mkdir(parents=True, exist_ok=True)
    archive = output / "hermes-client-handoff.tar.gz"
    staged = output / ".handoff-stage"
    if staged.exists(): shutil.rmtree(staged)
    staged.mkdir()
    shutil.copytree(package, staged / "package", dirs_exist_ok=True)
    bundle_dest = staged / "package" / "bundle" / "hermes-native-pipeline-0.21.2-full.bundle"
    bundle_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(bundle, bundle_dest)
    files = list(safe_files(staged / "package"))
    manifest = {"schema_version": 1, "bundle": {"version": "0.21.2", "head": EXPECTED_HEAD, "prerequisite_base": EXPECTED_BASE, "sha256": EXPECTED_BUNDLE_SHA256, "size": EXPECTED_BUNDLE_SIZE}, "profiles": list(PROFILES), "files": [{"path": rel, "size": src.stat().st_size, "sha256": sha256(src)} for src, rel in files]}
    manifest_path = staged / "package" / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    manifest_sha = sha256(manifest_path)
    with archive.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as gz:
            with tarfile.open(fileobj=gz, mode="w|") as tar:
                for source, relative in safe_files(staged / "package"):
                    add_file(tar, source, f"hermes-client-handoff/{relative}")
    archive_sha = sha256(archive)
    (output / "hermes-client-handoff.tar.gz.sha256").write_text(f"{archive_sha}  {archive.name}\n", encoding="utf-8")
    receipt = {"archive": archive.name, "archive_sha256": archive_sha, "archive_size": archive.stat().st_size, "manifest_sha256": manifest_sha, "profiles": list(PROFILES), "deterministic": True}
    (output / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(staged)
    print(json.dumps(receipt, sort_keys=True))
    return 0
if __name__ == "__main__": raise SystemExit(main())
