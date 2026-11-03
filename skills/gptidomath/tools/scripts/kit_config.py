#!/usr/bin/env python3
"""Load local settings and locate an existing synchronized workspace."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

DRIVE_NAMES = ("My Drive", "我的云端硬盘", "我的雲端硬碟")
DEFAULTS = {"workspace": None, "workspace_name": "AI-workspace", "redact": []}


def _validate(config: dict) -> dict:
    workspace = config.get("workspace")
    if workspace is not None and (not isinstance(workspace, str) or not workspace.strip()):
        raise ValueError("workspace must be a directory path or null")
    name = config.get("workspace_name", "AI-workspace")
    if (not isinstance(name, str) or not name.strip() or name in (".", "..")
            or re.search(r'[<>:"/\\|?*\x00-\x1f]', name)
            or name.endswith((".", " "))):
        raise ValueError("workspace_name must be one folder name")
    if re.fullmatch(r"(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", name):
        raise ValueError("workspace_name cannot be a reserved device name")
    words = config.get("redact", [])
    if not isinstance(words, list) or any(not isinstance(word, str) or not word.strip() for word in words):
        raise ValueError("redact must be a list of non-empty strings")
    return config


def load_config(config_path: str | Path | None = None) -> dict:
    """Relative configured paths use the config directory; env paths use cwd."""
    explicit = config_path or os.environ.get("GPTIDOMATH_CONFIG")
    path = Path(explicit).expanduser() if explicit else Path.home() / ".gptidomath" / "config.json"
    path = path.absolute()
    config = {**DEFAULTS, "redact": []}
    if path.exists() or explicit:
        loaded = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(loaded, dict):
            raise ValueError("Config must be a JSON object")
        config.update(loaded)
    override = os.environ.get("GPTIDOMATH_WORKSPACE")
    if override:
        config["workspace"] = override
    _validate(config)
    if config["workspace"]:
        resolved = Path(config["workspace"]).expanduser()
        if not resolved.is_absolute():
            resolved = (Path.cwd() if override else path.parent) / resolved
        config["workspace"] = str(resolved.resolve())
    return config


def _drive_roots() -> list[Path]:
    candidates: list[Path] = []
    home = Path.home()
    if sys.platform == "win32":
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            candidates.extend(Path(f"{letter}:/") / name for name in DRIVE_NAMES)
        folders = {home / "Google Drive", home / "GoogleDrive",
                   *home.glob("Google Drive*"), *home.glob("GoogleDrive*")}
        for folder in sorted(folders):
            if folder.is_dir():
                nested = [folder / name for name in DRIVE_NAMES if (folder / name).is_dir()]
                candidates.extend(nested or [folder])
    elif sys.platform == "darwin":
        for folder in sorted((home / "Library" / "CloudStorage").glob("GoogleDrive-*")):
            candidates.extend(folder / name for name in DRIVE_NAMES)
    roots: dict[str, Path] = {}
    for candidate in candidates:
        try:
            if candidate.is_dir():
                resolved = candidate.resolve()
                roots[os.path.normcase(str(resolved))] = resolved
        except OSError:
            continue
    return sorted(roots.values(), key=str)


def workspace_root(config: dict | None = None) -> Path:
    config = load_config() if config is None else _validate({**DEFAULTS, **config})
    explicit = os.environ.get("GPTIDOMATH_WORKSPACE") or config.get("workspace")
    if explicit:
        path = Path(explicit).expanduser()
    else:
        roots = _drive_roots()
        if len(roots) > 1:
            raise ValueError("Multiple Drive roots found; set workspace explicitly: " + ", ".join(map(str, roots)))
        if not roots:
            raise ValueError("No local Drive root found. Set workspace in ~/.gptidomath/config.json "
                             "or GPTIDOMATH_WORKSPACE to an existing synced folder or mount; "
                             "use drive_mirror.py pack --out for an upload package without Drive.")
        path = roots[0] / config["workspace_name"]
    if not path.is_dir():
        raise ValueError(f"Workspace directory does not exist: {path}. Create it locally or set an explicit path.")
    return path.resolve()


def selftest() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        settings = root / ".gptidomath"
        settings.mkdir()
        workspace = settings / "workspace"
        workspace.mkdir()
        path = settings / "config.json"
        with patch.dict(os.environ, {}, clear=True), patch.object(Path, "home", return_value=root):
            assert load_config() == DEFAULTS
            path.write_text(json.dumps({"workspace": "workspace", "redact": ["sample-word"]}), encoding="utf-8-sig")
            config = load_config()
            assert config["redact"] == ["sample-word"]
            assert workspace_root(config) == workspace.resolve()
            with patch.dict(os.environ, {"GPTIDOMATH_CONFIG": str(path), "GPTIDOMATH_WORKSPACE": str(root)}):
                assert workspace_root(load_config()) == root.resolve()
            with patch(__name__ + "._drive_roots", return_value=[root]):
                (root / "AI-workspace").mkdir()
                (root / "Research").mkdir()
                assert workspace_root({}) == (root / "AI-workspace").resolve()
                assert workspace_root({"workspace_name": "Research"}) == (root / "Research").resolve()
            for roots in ([], [root, workspace]):
                with patch(__name__ + "._drive_roots", return_value=roots):
                    try:
                        workspace_root({})
                    except ValueError:
                        pass
                    else:
                        raise AssertionError("Discovery must require an explicit choice")
            for invalid in ({"redact": "sample"}, {"redact": [""]}, {"workspace_name": "../escape"}, {"workspace_name": "NUL"}):
                try:
                    _validate(invalid)
                except ValueError:
                    pass
                else:
                    raise AssertionError("Invalid config accepted")
            with patch(__name__ + ".sys.platform", "darwin"):
                folder = root / "Library" / "CloudStorage" / "GoogleDrive-test" / DRIVE_NAMES[1]
                folder.mkdir(parents=True)
                assert _drive_roots() == [folder.resolve()]
    print("selftest PASS: kit_config (BOM, overrides, discovery, validation)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Config file; default ~/.gptidomath/config.json")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    try:
        if args.selftest:
            return selftest()
        print(workspace_root(load_config(args.config)))
        return 0
    except (ValueError, OSError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
