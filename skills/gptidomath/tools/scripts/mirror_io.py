#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Portable names and replace-in-place publishing for synced folders."""
from __future__ import annotations
import contextlib
import threading
import stat
import hashlib
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
REPLACE_TRIES = 8
REPLACE_DELAY = 0.25  # Seconds between retries while Drive or an editor holds the file.


def safe_segment(value: str | None, label: str = "name") -> str:
    """Return value when it is one folder/file name that works on Windows, macOS and Linux."""
    text = value or ""
    if not text or text in {".", ".."}:
        raise ValueError(f"{label} must be a single folder name, not {text!r}")
    if UNSAFE_CHARS.search(text):
        raise ValueError(f"{label} {text!r} must not contain path separators, a drive letter, or any of <>:\"|?*")
    if text[-1] in ". " or text[0] == " ":
        raise ValueError(f"{label} {text!r} must not start with a space or end with a dot or space")
    if text.split(".", 1)[0].upper() in WINDOWS_RESERVED:
        raise ValueError(f"{label} {text!r} is a reserved Windows device name")
    return text


def inside(parent: Path, child: Path, label: str = "path") -> Path:
    """Return child when it stays inside parent after resolving links and '..'."""
    base, target = Path(parent).resolve(), Path(child).resolve()
    if target != base and base not in target.parents:
        raise ValueError(f"{label} {child} leaves {parent}")
    return Path(child)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def replace_file(source: Path, target: Path) -> None:
    """os.replace, retried briefly: Windows refuses while another process has the target open."""
    for attempt in range(REPLACE_TRIES):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == REPLACE_TRIES - 1:
                raise
            time.sleep(REPLACE_DELAY)


def _umask() -> int:
    current = os.umask(0)
    os.umask(current)
    return current


def _publish(target: Path, prefix: str, fill, expected: str) -> None:
    target = Path(target)
    fd, pending = tempfile.mkstemp(prefix=prefix, suffix=".tmp", dir=target.parent)
    try:
        os.chmod(pending, 0o666 & ~_umask())  # mkstemp makes 0600; published files keep normal permissions.
        with os.fdopen(fd, "wb") as handle:
            fill(handle)
            handle.flush()
            os.fsync(handle.fileno())
        if sha256(Path(pending)) != expected:
            raise ValueError(f"Read-back checksum mismatch before publishing {target.name}")
        replace_file(Path(pending), target)
    finally:
        if os.path.exists(pending):
            os.unlink(pending)


def write_atomic(target: Path, data: bytes, prefix: str = ".mirror-") -> None:
    """Write beside target, verify, then replace it, so readers never see half a file."""
    _publish(target, prefix, lambda handle: handle.write(data), hashlib.sha256(data).hexdigest())


def copy_atomic(source: Path, target: Path, prefix: str = ".mirror-") -> None:
    def fill(handle):
        with open(source, "rb") as src:
            for block in iter(lambda: src.read(1 << 20), b""):
                handle.write(block)
    _publish(target, prefix, fill, sha256(Path(source)))


POLL_SECONDS = 0.2


def lock_dir() -> Path:
    base = Path(os.environ["GPTIDOMATH_HOME"]) if os.environ.get("GPTIDOMATH_HOME") else Path.home() / ".gptidomath"
    return base / "locks" / "mirror"


def _private_lock_dir() -> Path:
    """The lock folder, created 0700 like `~/.gptidomath` itself: its file names come from local paths."""
    directory = lock_dir()
    for path in (directory.parent.parent, directory.parent, directory):
        path.mkdir(mode=0o700, exist_ok=True)
    if os.name != "nt":
        for path in (directory.parent, directory):
            os.chmod(path, 0o700)  # also one an earlier kit created with the default mode
    return directory


def _try_lock(handle) -> bool:
    if os.name == "nt":
        import msvcrt
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            return False
        return True
    import fcntl
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return False
    return True


def _unlock(handle) -> None:
    if os.name == "nt":
        import msvcrt
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextlib.contextmanager
def held(target: Path, label: str, timeout: float):
    """Run the block while this process alone holds `target` (a REQUEST.md, a mirror folder)."""
    directory = _private_lock_dir()
    key = hashlib.sha256(os.path.normcase(str(Path(target).resolve())).encode("utf-8")).hexdigest()[:24]
    with open(directory / f"{key}.lock", "a+b") as handle:
        started, told = time.monotonic(), False
        while not _try_lock(handle):
            if time.monotonic() - started >= timeout:
                raise TimeoutError(f"another {label} of {target} has run for over {timeout:g}s; try again later")
            if not told:
                print(f"Waiting for another {label} of {target} to finish...", file=sys.stderr, flush=True)
                told = True
            time.sleep(POLL_SECONDS)
        try:
            yield
        finally:
            _unlock(handle)



def selftest() -> int:
    global REPLACE_DELAY
    checks = 0

    def check(value):
        nonlocal checks
        assert value
        checks += 1
    for good in ("sample", "kit-1.2", "my project"):
        check(safe_segment(good) == good)
    for bad in ("", ".", "..", "a/b", "a\\b", "/abs", "C:", "C:\\x", "\\\\host\\share", "CON", "nul.txt",
                "com1", "LPT9", "trail.", "trail ", " lead", "a?b", "tab\tname"):
        try:
            safe_segment(bad)
        except ValueError:
            checks += 1
        else:
            raise AssertionError(f"accepted {bad!r}")
    saved_delay, real_replace = REPLACE_DELAY, os.replace
    REPLACE_DELAY = 0
    try:
        with tempfile.TemporaryDirectory(prefix="safe-files-test-") as td:
            root = Path(td)
            check(inside(root, root / "a" / "b") == root / "a" / "b")
            try:
                inside(root / "a", root / "a" / ".." / "b")
            except ValueError:
                checks += 1
            else:
                raise AssertionError("escaped parent accepted")
            target = root / "REQUEST.md"
            target.write_bytes(b"old")
            failures = {"left": 2}

            def flaky(src, dst):
                if failures["left"]:
                    failures["left"] -= 1
                    raise PermissionError(32, "in use")
                real_replace(src, dst)
            with patch("os.replace", flaky):
                write_atomic(target, b"new", prefix=".request-")
            check(target.read_bytes() == b"new")
            check(sorted(p.name for p in root.iterdir()) == ["REQUEST.md"])

            def locked(src, dst):
                raise PermissionError(32, "in use")
            with patch("os.replace", locked):
                try:
                    write_atomic(target, b"lost", prefix=".request-")
                except PermissionError:
                    checks += 1
                else:
                    raise AssertionError("locked target reported success")
            check(target.read_bytes() == b"new")
            check(sorted(p.name for p in root.iterdir()) == ["REQUEST.md"])
            source = root / "source.bin"
            source.write_bytes(b"\0archive" * 1000)
            copy_atomic(source, root / "copy.bin")
            check((root / "copy.bin").read_bytes() == source.read_bytes())
            if os.name == "posix":
                check((root / "copy.bin").stat().st_mode & 0o777 == 0o666 & ~_umask())
    finally:
        REPLACE_DELAY = saved_delay
    print(f"selftest PASS: {checks} checks")
    return 0


def lock_selftest() -> int:
    checks = 0
    with tempfile.TemporaryDirectory(prefix="local-lock-test-") as td, patch.dict(os.environ, {"GPTIDOMATH_HOME": td}):
        target = Path(td) / "AI-workspace" / "task" / "REQUEST.md"
        inside, release = threading.Event(), threading.Event()

        def holder():
            with held(target, "request", timeout=5):
                inside.set()
                release.wait(5)
        thread = threading.Thread(target=holder)
        thread.start()
        assert inside.wait(5)
        try:
            with held(target, "request", timeout=0.3):
                raise AssertionError("a second holder got in")
        except TimeoutError as error:
            assert "another request" in str(error)
            checks += 1
        with held(Path(td) / "other" / "REQUEST.md", "request", timeout=0.3):
            checks += 1  # another target is not held up
        release.set()
        thread.join(5)
        with held(target, "request", timeout=1):
            checks += 1
        assert list(lock_dir().glob("*.lock")) and not target.parent.exists()
        checks += 1  # the lock stays local, out of the synced folder
        if os.name != "nt":
            assert all(stat.S_IMODE(p.stat().st_mode) == 0o700 for p in (lock_dir(), lock_dir().parent))
            checks += 1  # only this user can list the lock folder
    print(f"selftest PASS: {checks} checks")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(selftest() or lock_selftest())
    print(__doc__)
