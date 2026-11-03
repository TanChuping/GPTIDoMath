#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Mirror committed Git text and optional binary assets to a local sync folder.
Use push/status --repo PATH --name NAME [--config FILE] [--out DIR].
Push accepts --assets, --force and --report FILE (a local list of files kept back).
Pack --task TASK.md --out DIR creates one attachment with TASK.md, repo/, INDEX/ and _mirror/.
"""
from __future__ import annotations
import argparse
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch
import datetime as _dt
import hashlib
import time
import unicodedata
from code_index import EXT_KIND, build as index_build, verify as index_verify
from secret_patterns import RULES_VERSION, Redactor, local_identities
from mirror_io import copy_atomic, inside, safe_segment, write_atomic, sha256, held
from kit_config import load_config, workspace_root
from task_text import finalize

CHUNK = 200_000_000  # Local binary ZIP volume limit in bytes.
TEXT_MAX = 250 * 2 ** 20  # Maximum text ZIP size.
STORE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".ogg", ".mp3", ".mp4", ".webm", ".zip", ".gz", ".7z", ".woff2", ".ktx2", ".basis"}
RESERVED_TOP = {"index", "_mirror"}  # The text ZIP's own INDEX/ and _mirror/ folders.


def git(repo: Path, *args: str) -> str:
    r = subprocess.run(['git', '-C', str(repo), *args], capture_output=True)
    if r.returncode != 0:
        raise ValueError(f"git {' '.join(args)} failed: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout.decode('utf-8', 'replace')


def repo_root(start: Path) -> Path:
    return Path(git(start, 'rev-parse', '--show-toplevel').strip())


def _zinfo(name: str, mode: int, dt: tuple) -> zipfile.ZipInfo:
    zi = zipfile.ZipInfo(name, date_time=dt)
    zi.create_system = 3
    zi.external_attr = (mode & 511 | 32768) << 16
    zi.compress_type = zipfile.ZIP_STORED if Path(name).suffix.lower() in STORE_EXT else zipfile.ZIP_DEFLATED
    return zi


class ChunkWriter:
    def __init__(self, tmp: Path, stem: str):
        self.tmp, self.stem, self.parts, self.z, self.size = tmp, stem, [], None, 0

    def add(self, name: str, data: bytes, mode: int, dt: tuple) -> None:
        if self.z is None or (self.size and self.size + len(data) > CHUNK):
            self.close()
            p = self.tmp / f"{self.stem}.part{len(self.parts) + 1}"
            self.parts.append(p)
            self.z, self.size = zipfile.ZipFile(p, "w"), 0
        self.z.writestr(_zinfo(name, mode, dt), data)
        self.size += len(data)

    def close(self) -> None:
        if self.z is not None:
            self.z.close()
            self.z = None

    def finish(self) -> list[Path]:
        self.close()
        n = len(self.parts)
        out = []
        for i, p in enumerate(self.parts, 1):
            q = p.with_name(f"{self.stem}.zip" if n == 1 else f"{self.stem}-{i}of{n}.zip")
            p.rename(q)
            out.append(q)
        return out


def name_collisions(paths: list[str]) -> list[tuple[str, str]]:
    """Pairs that Windows or macOS would extract to one file: same name up to case or NFC/NFD."""
    seen: dict[str, str] = {}
    pairs = []
    for p in sorted(paths):
        key = unicodedata.normalize('NFC', p).casefold()
        if key in seen:
            pairs.append((seen[key], p))
        else:
            seen[key] = p
    return sorted(pairs)


def reserved_paths(paths: list[str]) -> list[str]:
    return sorted(p for p in paths if p.split('/', 1)[0].rstrip('/').casefold() in RESERVED_TOP)


def build(repo: Path, name: str, commit: str, tmp: Path, red: Redactor, want_text: bool, want_bin: bool) -> dict:
    info = git(repo, 'show', '-s', '--format=%H%n%ct%n%cI%n%s', commit).split('\n', 3)
    full, ct, cdate, subject = (info[0], int(info[1]), info[2], info[3].strip())
    subject = red.text(subject.encode('utf-8'))[0].decode('utf-8')
    dt = time.gmtime(max(ct, 315532800))[:6]
    proc = subprocess.Popen(["git", "-C", str(repo), "archive", "--format=tar", full], stdout=subprocess.PIPE)
    texts: dict[str, tuple[bytes, int]] = {}
    bins: list[tuple[str, int, str]] = []
    redlog: list[tuple[str, int, str]] = []
    excluded: list[str] = []
    blocked: list[tuple[str, str]] = []
    non_utf8: list[str] = []
    members: list[str] = []
    kept: list[str] = []
    fp = hashlib.sha256()
    bw = ChunkWriter(tmp, f'{name}-bin') if want_bin else None
    with tarfile.open(fileobj=proc.stdout, mode='r|') as tf:
        for m in tf:
            members.append(m.name)
            if not m.isfile():
                if not m.isdir():
                    blocked.append((m.name, "unsupported archive entry"))
                continue
            try:
                for component in m.name.split('/'):
                    safe_segment(component, "archive path")
            except ValueError:
                blocked.append((m.name, "unsafe archive path"))
                continue
            data = tf.extractfile(m).read()
            v = red.scan(m.name, data)
            if v.kind == 'blocked':
                blocked.append((m.name, v.reason))
                if v.reason.startswith('binary'):
                    excluded.append(m.name)
                continue
            kept.append(m.name)
            if v.kind == 'text':
                if v.note == 'non-utf8':
                    non_utf8.append(m.name)
                redlog += [(m.name, ln, k) for ln, k in v.hits]
                if want_text:
                    texts[m.name] = (v.data, m.mode)
                continue
            digest = hashlib.sha1(data).hexdigest()
            fp.update(f'{m.name}\x00{digest}\n'.encode('utf-8', 'surrogateescape'))
            bins.append((m.name, len(data), digest[:12]))
            if bw:
                bw.add(m.name, data, m.mode, dt)
    if proc.wait() != 0:
        raise ValueError("git archive failed")
    clash = reserved_paths(members)
    if clash:
        raise ValueError("The repository has paths in the mirror's own INDEX/ or _mirror/ folders: "
                         + ", ".join(clash[:10]) + "; rename them or mark them export-ignore")
    out = {'commit': full, 'commit_date': cdate, 'subject': subject, 'bin_fingerprint': fp.hexdigest(), 'bin_count': len(bins),
           'excluded': excluded, 'blocked': blocked, 'non_utf8': non_utf8, 'collisions': name_collisions(kept),
           'text_zip': None, 'bin_zips': bw.finish() if bw else [], 'text_count': len(texts), 'redactions': redlog}
    if not want_text:
        return out
    stamp = {'project': name, 'layer': 'text', 'commit': full, 'commit_date': cdate, 'subject': subject, 'note': 'Committed text only; binary inventory is in _mirror/binary-files.tsv.'}
    meta = {'_mirror/STAMP.json': json.dumps(stamp, ensure_ascii=False, indent=1).encode('utf-8'), '_mirror/binary-files.tsv': ('path\tbytes\tsha1_12\n' + ''.join((f'{p}\t{n}\t{h}\n' for p, n, h in bins))).encode('utf-8', 'surrogateescape'), '_mirror/redactions.tsv': ('path\tline\tkind\n' + ''.join((f'{p}\t{ln}\t{k}\n' for p, ln, k in redlog))).encode('utf-8', 'surrogateescape')}
    meta['_mirror/excluded-files.json'] = json.dumps(
        [{'path': shown(p, reason), 'reason': reason} for p, reason in blocked],
        ensure_ascii=False, indent=2).encode('utf-8')
    entries = sorted(((k, v[0]) for k, v in texts.items()))
    idx = tmp / 'INDEX'
    index_build(entries, idx)
    bad = index_verify({k: v for k, v in entries if Path(k).suffix.lower() in EXT_KIND}, idx)
    if bad:
        raise ValueError(f'Index declaration mismatch: {bad[:3]}')
    zp = inside(tmp, tmp / f'{name}-text.zip', 'text archive')
    with zipfile.ZipFile(zp, 'w') as z:
        for k, data in entries:
            z.writestr(_zinfo(k, texts[k][1], dt), data)
        for k, data in meta.items():
            z.writestr(_zinfo(k, 420, dt), data)
        for f in sorted(idx.iterdir()):
            z.writestr(_zinfo('INDEX/' + f.name, 420, dt), f.read_bytes())
    if zp.stat().st_size > TEXT_MAX:
        raise ValueError(f'Text archive exceeds local {TEXT_MAX} byte policy; use export-ignore for large generated files')
    out['text_zip'] = zp
    return out


def commit_files(repo: Path, files: dict[str, bytes], message: str) -> None:
    """Commit exact paths through the index, so case-only twins work on case-insensitive disks."""
    for path, data in files.items():
        sha = subprocess.run(['git', '-C', str(repo), 'hash-object', '-w', '--stdin'], input=data,
                             capture_output=True, check=True).stdout.decode().strip()
        subprocess.run(['git', '-C', str(repo), 'update-index', '--add', '--cacheinfo', f'100644,{sha},{path}'],
                       check=True, capture_output=True)
    subprocess.run(['git', '-C', str(repo), 'commit', '-qm', message], check=True, capture_output=True)



def read_mirror(d: Path) -> dict:
    try:
        value = json.loads((d / "MIRROR.json").read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def new_layer(files: list[Path], commit: str, count: int, **extra) -> dict:
    return {'files': [f.name for f in files], 'bytes': [f.stat().st_size for f in files], 'sha256': [sha256(f) for f in files], 'file_count': count, 'commit': commit, **extra}


def layer_ok(dest: Path, layer: dict | None) -> bool:
    """Published volumes match the manifest byte for byte; a same-size corruption fails here."""
    if not isinstance(layer, dict):
        return False
    files, sizes, hashes = (layer.get(k) for k in ("files", "bytes", "sha256"))
    if not all(isinstance(values, list) for values in (files, sizes, hashes)):
        return False
    if len(files) != len(sizes) or len(files) != len(hashes):
        return False
    try:
        return all(safe_segment(name) == name and inside(dest, dest / name).is_file()
                   and (dest / name).stat().st_size == size and sha256(dest / name) == digest
                   for name, size, digest in zip(files, sizes, hashes))
    except (ValueError, OSError, TypeError):
        return False


def policy_fingerprint(red: Redactor) -> str:
    rules = [(word, pattern.pattern, replacement) for word, pattern, replacement in red.words]
    return hashlib.sha256(json.dumps([RULES_VERSION, rules, red.bin_needles], sort_keys=True).encode()).hexdigest()


def shown(path: str, reason: str) -> str:
    # A path that matched a private term must not reach the synced manifest.
    return f"<path withheld: {reason[6:]}>" if reason.startswith("path: ") else path


def print_summary(result: dict) -> None:
    blocked = result["blocked"]
    if blocked:
        print(f"{len(blocked)} files not uploaded (listed in MIRROR.json excluded_files):")
        for path, reason in blocked:
            note = "; path withheld from MIRROR.json" if reason.startswith("path: ") else ""
            print(f"  {path}  ({reason}{note})")
    if result["non_utf8"]:
        print(f"warning: {len(result['non_utf8'])} non-UTF-8 text files uploaded unchanged; no private term or "
              "credential pattern was found, but only UTF-8 text is redacted. Convert them to UTF-8 to be sure:")
        for path in result["non_utf8"]:
            print(f"  {path}")
    if result["collisions"]:
        print("warning: names that differ only by case or Unicode normalization; they overwrite each other "
              "when extracted on Windows or macOS:")
        for first, second in result["collisions"]:
            print(f"  {first}  <->  {second}")




def build_manifest(name: str, head: str, result: dict, policy: str, layers: dict, dirty: int, prev: dict, need_text: bool) -> dict:
    kinds = {}
    for _path, _line, kind in result["redactions"]:
        kinds[kind] = kinds.get(kind, 0) + 1
    return {
        "tool": "gptidomath/drive-mirror/1", "project": name,
        "commit": head, "commit_date": result["commit_date"], "subject": result["subject"],
        "pushed_at": _dt.datetime.now().astimezone().isoformat(timespec="microseconds"),
        "worktree": {"uncommitted_changes_excluded": dirty}, "redaction_policy": policy, "layers": layers,
        "redactions": {"count": len(result["redactions"]), "by_kind": kinds,
            "where": "text archive: _mirror/redactions.tsv"} if need_text else prev.get("redactions"),
        "excluded_binary_files": result["excluded"],
        "excluded_files": [{"path": shown(p, r), "reason": r} for p, r in result["blocked"]],
        "how_to": ["Extract text into a new empty directory, then optionally extract binary volumes there.",
            "Check the text archive's _mirror/STAMP.json commit against MIRROR.json and the requested commit.",
            "Wait for Drive sync, then verify the files through the connected app.",
            "Binary same_as_text_commit describes content equivalence; its commit may be older.",
            "Files in excluded_files were kept back on purpose; ask for them rather than guessing.",
            "Inspect the first export before sharing."],
    }


def write_report(path: Path, name: str, head: str, dest: Path, result: dict) -> None:
    """Local only: full paths, including ones withheld from the synced manifest."""
    path.write_text(json.dumps({"project": name, "commit": head, "destination": str(dest),
        "not_uploaded": [{"path": p, "reason": r} for p, r in result["blocked"]],
        "non_utf8_uploaded_unchanged": result["non_utf8"], "name_collisions": result["collisions"]},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Local report: {path}")


# A push of one mirror waits this long for another push of it to finish.
LOCK_TIMEOUT = 1800

NAME_RE_T = r"^{p}-(?:text|bin)(?:-\d+of\d+)?\.zip$"


def mirror_dir(repo: Path, name: str | None = None, settings: dict | None = None) -> Path:
    parent = workspace_root(settings) / "repos"
    return inside(parent, parent / safe_segment(repo.name if name is None else name, "--name"), "mirror folder")


def push(repo: Path, name: str | None, assets: bool, force: bool, out_dir: Path | None,
         settings: dict | None = None, identities: list[str] | None = None, report: Path | None = None) -> int:
    root = repo_root(repo)
    label = safe_segment(root.name if name is None else name, "--name")
    settings = load_config() if settings is None else settings
    dest = Path(out_dir) if out_dir is not None else mirror_dir(root, label, settings)
    # Two pushes of one mirror at once would each delete the volumes the other just wrote
    # and leave a MIRROR.json that names the wrong archives.
    with held(dest, "mirror push", LOCK_TIMEOUT):
        return _push(root, label, assets, force, dest, settings, identities, report)


def _push(repo: Path, name: str | None, assets: bool, force: bool, out_dir: Path | None,
          settings: dict | None = None, identities: list[str] | None = None, report: Path | None = None) -> int:
    repo = repo_root(repo)
    name = safe_segment(repo.name if name is None else name, "--name")
    settings = load_config() if settings is None else settings
    dest = Path(out_dir) if out_dir is not None else mirror_dir(repo, name, settings)
    if report is not None and Path(report).resolve().is_relative_to(dest.resolve()):
        raise ValueError("--report must be outside the mirror folder; it lists private paths and must stay local")
    dest.mkdir(parents=True, exist_ok=True)
    head = git(repo, "rev-parse", "HEAD").strip()
    prev = read_mirror(dest)
    if prev and prev.get("project") != name:
        raise ValueError("Destination contains another project's MIRROR.json; choose a separate --out")
    layers = prev.get("layers", {})
    red = Redactor(local_identities(repo) if identities is None else identities, settings.get("redact", []))
    policy = policy_fingerprint(red)
    policy_changed = prev.get("redaction_policy") != policy
    text_layer, bin_layer = layers.get("text") or {}, layers.get("bin") or {}
    need_text = force or policy_changed or text_layer.get("commit") != head or not layer_ok(dest, text_layer)
    need_bin = assets and (force or policy_changed or bin_layer.get("commit") != head or not layer_ok(dest, bin_layer))
    dirty = len(git(repo, "status", "--porcelain").splitlines())
    if not need_text and not need_bin:
        kept_back = len(prev.get("excluded_files") or [])
        print(f"Up to date: {dest} at {head[:10]}; {dirty} uncommitted changes excluded"
              + (f"; {kept_back} files not uploaded (see MIRROR.json; --force rebuilds the list)" if kept_back else ""))
        if report is not None:
            print("No --report written: nothing was rebuilt; add --force to rebuild and report")
        return 0
    with tempfile.TemporaryDirectory(prefix="drive-mirror-") as td:
        result = build(repo, name, head, Path(td), red, want_text=need_text, want_bin=need_bin)
        layers = dict(layers)
        writes = []
        if policy_changed and not assets:
            layers.pop("bin", None)
        if need_text:
            layers["text"] = new_layer([result["text_zip"]], head, result["text_count"])
            writes.append(result["text_zip"])
        old_bin = layers.get("bin")
        if need_bin and not force and old_bin and old_bin.get("fingerprint") == result["bin_fingerprint"] and layer_ok(dest, old_bin):
            layers["bin"] = dict(old_bin, commit=head)
            print("Binary content unchanged; retaining existing volumes")
        elif need_bin:
            layers["bin"] = new_layer(result["bin_zips"], head, result["bin_count"], fingerprint=result["bin_fingerprint"])
            writes.extend(result["bin_zips"])
        if layers.get("bin"):
            layers["bin"]["same_as_text_commit"] = layers["bin"].get("fingerprint") == result["bin_fingerprint"]
        owned = re.compile(NAME_RE_T.format(p=re.escape(name)))
        for item in writes:
            # Written beside the target, checked, then swapped in: readers never see half an archive.
            copy_atomic(item, inside(dest, dest / item.name, "archive"))
        keep = {filename for layer in layers.values() for filename in layer["files"]}
        for item in dest.iterdir():
            if item.is_file() and owned.fullmatch(item.name) and item.name not in keep:
                item.unlink()
        manifest = build_manifest(name, head, result, policy, layers, dirty, prev, need_text)
        # This is the final published file, after archive read-back and stale-volume cleanup.
        write_atomic(dest / "MIRROR.json", (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print_summary(result)
    if report is not None:
        write_report(Path(report), name, head, dest, result)
    print(f"Mirrored {head[:10]} to {dest}; wrote {len(writes)} archives; {dirty} uncommitted changes excluded")
    return 0


def status(repo: Path, name: str | None, out_dir: Path | None = None, settings: dict | None = None) -> int:
    repo = repo_root(repo)
    name = safe_segment(repo.name if name is None else name, "--name")
    dest = Path(out_dir) if out_dir is not None else mirror_dir(repo, name, settings)
    head = git(repo, "rev-parse", "HEAD").strip()
    manifest = read_mirror(dest)
    ok = text_layer_current(dest, manifest, name, head)
    print(f"{dest}: {'up to date' if ok else 'missing, outdated, or damaged'}; HEAD {head[:10]}")
    binary = (manifest.get("layers") or {}).get("bin")
    if binary and (binary.get("same_as_text_commit") is False or not layer_ok(dest, binary)):
        print("Binary layer differs or is damaged; use push --assets")
    return 0 if ok else 1


def text_layer_current(dest: Path, manifest: dict, name: str, head: str) -> bool:
    layer = (manifest.get("layers") or {}).get("text") or {}
    return manifest.get("project") == name and layer.get("commit") == head and layer_ok(dest, layer)


def current_mirror(repo: Path, name: str | None = None, settings: dict | None = None) -> tuple[str, str, int]:
    """(project, commit, uncommitted changes) for a repository whose published mirror matches HEAD."""
    repo = repo_root(repo)
    name = safe_segment(repo.name if name is None else name, "--name")
    dest = mirror_dir(repo, name, settings)
    head = git(repo, "rev-parse", "HEAD").strip()
    if not text_layer_current(dest, read_mirror(dest), name, head):
        raise ValueError(f"the mirror in {dest} is missing, outdated or damaged (HEAD {head[:10]}); "
                         "run drive_mirror.py push first")
    return name, head, len(git(repo, "status", "--porcelain").splitlines())


def pack(repo: Path, name: str | None, task: Path, out_dir: Path, assets: bool = False,
         settings: dict | None = None, identities: list[str] | None = None) -> int:
    """A single attachment: committed, redacted repository plus the supplied task."""
    repo = repo_root(repo)
    name = safe_segment(repo.name if name is None else name, "--name")
    settings = load_config() if settings is None else settings
    red = Redactor(local_identities(repo) if identities is None else identities, settings.get("redact", []))
    try:
        task_text = Path(task).read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("TASK.md must be UTF-8 text") from None
    head = git(repo, "rev-parse", "HEAD").strip()
    task_text = finalize(task_text, "package", {"TASK_FILE": "TASK.md", "PROJECT": name, "COMMIT": head})
    task_scan = red.scan("TASK.md", task_text.encode("utf-8"))
    if task_scan.kind != "text":
        raise ValueError("TASK.md must be readable text without an incomplete private key")
    target = Path(out_dir) / f"{name}-package.zip"
    if Path(task).resolve() == target.resolve():
        raise ValueError("--task must differ from the package output path")
    with held(target, "package", LOCK_TIMEOUT), tempfile.TemporaryDirectory(prefix="mirror-pack-") as td:
        temporary = Path(td)
        result = build(repo, name, head, temporary, red, True, assets)
        package = temporary / target.name
        index_entries = [("TASK.md", task_scan.data)]
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(_zinfo("TASK.md", 0o644, time.localtime()[:6]), task_scan.data)
            with zipfile.ZipFile(result["text_zip"]) as source:
                for entry in source.infolist():
                    if entry.filename.startswith("INDEX/"):
                        continue
                    data = source.read(entry)
                    if not entry.filename.startswith("_mirror/"):
                        entry.filename = "repo/" + entry.filename
                        index_entries.append((entry.filename, data))
                    archive.writestr(entry, data)
            for volume in result["bin_zips"]:
                with zipfile.ZipFile(volume) as source:
                    for entry in source.infolist():
                        data = source.read(entry)
                        entry.filename = "repo/" + entry.filename
                        archive.writestr(entry, data)
            index_dir = temporary / "package-index"
            index_build(sorted(index_entries), index_dir)
            if index_verify(dict(index_entries), index_dir):
                raise ValueError("Package index declaration mismatch")
            for item in sorted(index_dir.iterdir()):
                archive.writestr(_zinfo("INDEX/" + item.name, 0o644, time.localtime()[:6]), item.read_bytes())
            manifest = build_manifest(name, head, result, policy_fingerprint(red), {},
                                      len(git(repo, "status", "--porcelain").splitlines()), {}, True)
            manifest.update({"layout": {"task": "TASK.md", "repository": "repo/"},
                             "assets_included": assets, "task_redactions": len(task_scan.hits)})
            archive.writestr(_zinfo("_mirror/MIRROR.json", 0o644, time.localtime()[:6]),
                             json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))
        target.parent.mkdir(parents=True, exist_ok=True)
        copy_atomic(package, inside(target.parent, target, "package"))
    print_summary(result)
    size = target.stat().st_size
    print(f"Package: {target} ({size} bytes; {size / 2**20:.2f} MiB); commit {head[:10]}")
    print(f"Uncommitted repository changes excluded: {manifest['worktree']['uncommitted_changes_excluded']}")
    print("Large binaries belong on the Drive route: push --assets, then reference the mirror in TASK.md.")
    return 0


def _expect_error(action, *needles) -> int:
    try:
        action()
    except ValueError as exc:
        assert all(n in str(exc) for n in needles), str(exc)
        return 1
    raise AssertionError(f"expected an error mentioning {needles}")


def selftest() -> int:
    checks = 0
    def check(value, label=""):
        nonlocal checks
        assert value, label
        checks += 1
    global CHUNK
    saved_chunk = CHUNK
    try:
        # Its own GPTIDOMATH_HOME: the push locks of a selftest never touch the real ~/.gptidomath.
        with tempfile.TemporaryDirectory(prefix="drive-mirror-test-") as td, patch.dict(os.environ, {"GPTIDOMATH_HOME": td}):
            root = Path(td)
            repo = root / "sample"
            (repo / "src").mkdir(parents=True)
            def run(*args, at=repo):
                subprocess.run(["git", "-C", str(at), *args], check=True, capture_output=True)
            run("init", "-q")
            run("config", "core.autocrlf", "false")
            run("config", "user.email", "test@example.invalid")
            run("config", "user.name", "Sample Test")
            key_begin = "-----BEGIN " + "RSA PRIVATE KEY-----"
            key_end = "-----END " + "RSA PRIVATE KEY-----"
            email = "me@" + "example.com"
            secret = "abcdefgh" + "ijklmnop"
            access_key = "AKIA" + "0123456789ABCDEF"
            pw = "PASS" + "WORD"
            source = ('# C:/Users/' + 'AliceNine/a and /home/' + 'bobfive/b and /Users/Public/c\n'
                      + f'def first():\n    token = "{secret}"\n'
                      + f'    return "PrivateName Zed12345 {email} {access_key}"\n'
                      + f'# {key_begin}\n# secret key lines\n# {key_end}\n')
            (repo / "src" / "sample.py").write_text(source, encoding="utf-8")
            (repo / "orphan.txt").write_text(key_begin + "\nfollowing line\n", encoding="utf-8")
            (repo / "src" / "sample.ts").write_text("export function ready() { return true; }\n", encoding="utf-8")
            (repo / "one.png").write_bytes(b"\0" + b"x" * 300)
            (repo / "two.png").write_bytes(b"\0" + b"y" * 300)
            (repo / "private.bin").write_bytes(b"\0" + "Zed12345".encode("utf-16-be"))
            (repo / "skip.txt").write_text("skip", encoding="utf-8")
            (repo / ".gitattributes").write_text("skip.txt export-ignore\n", encoding="utf-8")
            (repo / ".env").write_text(f"{pw}=Zq7env\nAPI_" + "KEY=Zq7short\n", encoding="utf-8")
            (repo / "settings.ini").write_bytes(f"{pw}=Zq7wide\r\n".encode("utf-16"))
            (repo / "legacy-hit.txt").write_bytes("\u00e9\u00e0 \u00e9x\n".encode("cp1252"))
            (repo / "legacy-clean.txt").write_bytes("\u00e9\u00e0 notes\n".encode("cp1252"))
            (repo / "PrivateName-notes.txt").write_text("plain\n", encoding="utf-8")
            run("add", "-A")
            run("commit", "-qm", "first PrivateName")
            (repo / "src" / "sample.py").write_text("uncommitted value", encoding="utf-8")
            out = root / "output"
            settings = {"redact": ["PrivateName", "\u00e9x"]}
            identities = ["Zed12345"]
            CHUNK = 350
            report, printed = root / "local-report.json", io.StringIO()
            with contextlib.redirect_stdout(printed):
                check(push(repo, "sample", True, False, out, settings, identities, report) == 0)
            shown = printed.getvalue()
            first = read_mirror(out)
            head = git(repo, "rev-parse", "HEAD").strip()
            check(first["commit"] == head)
            check("PrivateName" not in first["subject"])
            check(first["layers"]["bin"]["files"] == ["sample-bin-1of2.zip", "sample-bin-2of2.zip"])
            check(first["excluded_binary_files"] == ["private.bin"])
            check({e["path"]: e["reason"] for e in first["excluded_files"]} == {
                "<path withheld: personal>": "path: personal", "legacy-hit.txt": "non-UTF-8 text: personal",
                "orphan.txt": "unclosed private key", "private.bin": "binary: private term or identity"})
            manifest_text = (out / "MIRROR.json").read_text(encoding="utf-8")
            check(not any(t in manifest_text for t in ("PrivateName", "\u00e9x", "Zq7")))
            check(all(p in shown for p in ("4 files not uploaded", "PrivateName-notes.txt", "orphan.txt", "legacy-clean.txt")))
            check("Zq7" not in shown and "\u00e9x" not in shown)
            local = json.loads(report.read_text(encoding="utf-8"))
            check("PrivateName-notes.txt" in {e["path"] for e in local["not_uploaded"]})
            check(first["worktree"]["uncommitted_changes_excluded"] == 1)
            with zipfile.ZipFile(out / "sample-text.zip") as z:
                names = z.namelist()
                check(not {"orphan.txt", "legacy-hit.txt", "PrivateName-notes.txt"} & set(names))
                check(z.read("legacy-clean.txt") == "\u00e9\u00e0 notes\n".encode("cp1252"))
                check("Zq7" not in z.read("settings.ini").decode("utf-16") and "Zq7" not in z.read(".env").decode())
                data = z.read("src/sample.py").decode()
                check("uncommitted value" not in data and "def first" in data)
                check("skip.txt" not in names)
                check("INDEX/INDEX-functions.tsv" in names)
                check(len(names) == len(set(names)))
                check(json.loads(z.read("_mirror/STAMP.json"))["commit"] == head)
                for token in ("AliceNine", "bobfive", "PrivateName", "Zed12345", email, "AKIA0123", secret, "secret key lines"):
                    check(token not in data)
                check("/Users/Public/c" in data)
            check(push(repo, "sample", True, False, out, settings, identities) == 0)
            check(read_mirror(out)["pushed_at"] == first["pushed_at"])
            check(status(repo, "sample", out, settings) == 0)
            damaged = bytearray((out / "sample-text.zip").read_bytes())
            damaged[len(damaged) // 2] ^= 0xFF
            (out / "sample-text.zip").write_bytes(bytes(damaged))
            check(status(repo, "sample", out, settings) == 1)
            check(push(repo, "sample", True, False, out, settings, identities) == 0)
            check(status(repo, "sample", out, settings) == 0)
            (repo / "src" / "sample.py").write_text("def updated():\n    return 2\n", encoding="utf-8")
            run("commit", "-qam", "second")
            old_time = (out / first["layers"]["bin"]["files"][0]).stat().st_mtime_ns
            check(push(repo, "sample", False, False, out, settings, identities) == 0)
            second = read_mirror(out)
            check(second["layers"]["bin"]["commit"] == head)
            check(second["layers"]["bin"]["same_as_text_commit"] is True)
            check(push(repo, "sample", True, False, out, settings, identities) == 0)
            check((out / first["layers"]["bin"]["files"][0]).stat().st_mtime_ns == old_time)
            (out / "unrelated.txt").write_text("retain", encoding="utf-8")
            (repo / "two.png").unlink()
            run("commit", "-qam", "third")
            check(push(repo, "sample", True, False, out, settings, identities) == 0)
            check(read_mirror(out)["layers"]["bin"]["files"] == ["sample-bin.zip"])
            check((out / "unrelated.txt").read_text(encoding="utf-8") == "retain")
            check(not (out / "sample-bin-1of2.zip").exists())
            old = 10 ** 18  # --force must rewrite even unchanged volumes.
            os.utime(out / "sample-bin.zip", ns=(old, old))
            check(push(repo, "sample", True, True, out, settings, identities) == 0)
            check((out / "sample-bin.zip").stat().st_mtime_ns > old)
            prior = read_mirror(out)["pushed_at"]
            check(push(repo, "sample", False, False, out, {"redact": ["updated"]}, identities) == 0)
            check(read_mirror(out)["pushed_at"] != prior)
            with zipfile.ZipFile(out / "sample-text.zip") as z:
                check("updated" not in z.read("src/sample.py").decode())
            checks += _expect_error(lambda: push(repo, "other-project", False, False, out, settings, identities), "another project")
            checks += _expect_error(lambda: push(repo, "sample", False, True, out, settings, identities, out / "r.json"), "--report")
            never = root / "never"
            for bad in ("../escape", "CON", "", "a/b", "C:x", "trail."):
                checks += _expect_error(lambda: push(repo, bad, False, False, never / "out", settings, identities), "--name")
            check(not never.exists() and not (root / "escape-text.zip").exists())
            task = root / "TASK.md"
            task.write_text("<!-- agent note -->\nInspect the committed implementation.\n<!-- BEGIN drive -->\n"
                            "Write {{WORKSPACE}}/DONE.txt.\n<!-- END drive -->\n<!-- BEGIN package -->\nRead repo/ of {{PROJECT}} at {{COMMIT}}.\n"
                            "<!-- END package -->\n", encoding="utf-8-sig")
            package_dir = root / "packages"
            check(pack(repo, "sample", task, package_dir, True, settings, identities) == 0)
            with zipfile.ZipFile(package_dir / "sample-package.zip") as archive:
                check({"TASK.md", "repo/src/sample.py", "repo/one.png", "INDEX/INDEX-files.tsv",
                       "_mirror/MIRROR.json", "_mirror/STAMP.json"} <= set(archive.namelist()))
                check(len(archive.namelist()) == len(set(archive.namelist())))
                check(archive.read("TASK.md") == ("Inspect the committed implementation.\nRead repo/ of sample at "
                                                  + git(repo, "rev-parse", "HEAD").strip() + ".\n").encode())
                check(json.loads(archive.read("_mirror/MIRROR.json"))["commit"] == git(repo, "rev-parse", "HEAD").strip())
                check(b"repo/src/sample.py" in archive.read("INDEX/INDEX-functions.tsv"))
            check(pack(repo, "text-only", task, package_dir, False, settings, identities) == 0)
            with zipfile.ZipFile(package_dir / "text-only-package.zip") as archive:
                check("repo/one.png" not in archive.namelist())
            unfilled = root / "TASK-unfilled.md"
            unfilled.write_text("Read {{WORKSPACE}}/REQUEST.md.\n", encoding="utf-8")
            checks += _expect_error(lambda: pack(repo, "unfilled", unfilled, package_dir, False, settings, identities),
                                    "unfilled placeholders")
            check(not (package_dir / "unfilled-package.zip").exists())
            input_target = package_dir / "input-package.zip"
            input_bytes = b"This task must not be overwritten.\n"
            input_target.write_bytes(input_bytes)
            checks += _expect_error(
                lambda: pack(repo, "input", input_target, package_dir, False, settings, identities),
                "--task must differ")
            check(input_target.read_bytes() == input_bytes)
            twins = root / "twins"
            twins.mkdir()
            for args in (("init", "-q"), ("config", "core.autocrlf", "false"), ("config", "user.email", "t@example.invalid"), ("config", "user.name", "Twin Test")):
                run(*args, at=twins)
            commit_files(twins, {"Foo.txt": b"a\n", "foo.txt": b"b\n"}, "twins")
            printed = io.StringIO()
            with contextlib.redirect_stdout(printed):
                check(push(twins, "twins", False, False, root / "twins-out", {}, []) == 0)
            check("Foo.txt  <->  foo.txt" in printed.getvalue())
            commit_files(twins, {"_Mirror/notes.md": b"x\n"}, "clash")
            checks += _expect_error(lambda: push(twins, "twins", False, False, root / "twins-out", {}, []), "_Mirror/notes.md")
    finally:
        CHUNK = saved_chunk
    print(f"selftest PASS: {checks} checks")
    return 0


def main(argv: list[str]) -> int:
    if argv == ["--selftest"]:
        return selftest()
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("push", "status", "pack"):
        cmd = sub.add_parser(command)
        cmd.add_argument("--repo", type=Path, default=Path("."))
        cmd.add_argument("--name")
        cmd.add_argument("--config")
        cmd.add_argument("--out", type=Path, required=command == "pack")
        if command in {"push", "pack"}:
            cmd.add_argument("--assets", action="store_true")
        if command == "pack":
            cmd.add_argument("--task", type=Path, required=True)
        if command == "push":
            cmd.add_argument("--force", action="store_true")
            cmd.add_argument("--report", type=Path, help="local JSON listing files kept back, with full paths")
    args = parser.parse_args(argv)
    try:
        settings = load_config(args.config)
        if args.command == "status":
            return status(args.repo, args.name, args.out, settings)
        if args.command == "pack":
            return pack(args.repo, args.name, args.task, args.out, args.assets, settings)
        return push(args.repo, args.name, args.assets, args.force, args.out, settings, report=args.report)
    except (ValueError, OSError, subprocess.SubprocessError, tarfile.TarError, zipfile.BadZipFile) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    sys.exit(main(sys.argv[1:]))
