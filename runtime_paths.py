"""Prepare a writable runtime directory before importing application modules."""

import json
import os
import shutil
import sys
from pathlib import Path


def user_data_directory():
    override = os.environ.get("JUVION_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Juvion"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Juvion"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "juvion"


def initialize_runtime():
    """Keep legacy relative paths working without writing into the installation.

    Source runs keep their existing repository data. Frozen builds use the OS
    user data directory and refresh bundled assets once per release. Existing
    installation data is copied on first launch, leaving the originals intact.
    """
    if not getattr(sys, "frozen", False):
        root = Path(__file__).resolve().parent
        os.chdir(root)
        return root

    bundle = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    root = user_data_directory()
    root.mkdir(parents=True, exist_ok=True)
    migration_marker = root / ".migration-complete"
    if not migration_marker.exists():
        previous = Path(sys.executable).resolve().parent
        for name in ("Projects", "settings.json", "conversations.json", "projects.json", "project_settings.json", "prompts.json"):
            source, target = previous / name, root / name
            if source.exists() and not target.exists() and source != target:
                if source.is_dir():
                    shutil.copytree(source, target)
                else:
                    shutil.copy2(source, target)
        migration_marker.touch()

    version_file = bundle / "version.json"
    version = json.loads(version_file.read_text(encoding="utf-8"))["version"]
    marker = root / ".resources-version"
    if not marker.exists() or marker.read_text(encoding="utf-8") != version:
        shutil.copytree(bundle / "assets", root / "assets", dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("editor_settings.json", "color_settings.json"))
        shutil.copy2(version_file, root / "version.json")
        marker.write_text(version, encoding="utf-8")
    (root / "Projects").mkdir(exist_ok=True)
    os.chdir(root)
    return root
