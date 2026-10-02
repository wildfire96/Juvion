"""Single application version, shared by packaging and build metadata."""
import json
from pathlib import Path

__version__ = json.loads((Path(__file__).resolve().parent / "version.json").read_text(encoding="utf-8"))["version"]
