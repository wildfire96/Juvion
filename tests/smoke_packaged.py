"""Verify a native Juvion executable with disposable user data."""
import argparse
import os
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    args = parser.parse_args()
    executable = args.executable.resolve()
    if not executable.is_file():
        parser.error("Executable not found: {}".format(executable))
    with tempfile.TemporaryDirectory(prefix="juvion-package-") as directory:
        root = Path(directory)
        data = root / "data"
        environment = os.environ.copy()
        environment["JUVION_DATA_DIR"] = str(data)
        environment["QT_QPA_PLATFORM"] = "offscreen"
        result = subprocess.run([str(executable), "--smoke-test"], cwd=root, env=environment,
                                capture_output=True, text=True, timeout=90)
        if result.returncode or not (data / ".smoke-ready").is_file():
            raise RuntimeError("Packaged startup failed ({}).\n{}\n{}".format(result.returncode, result.stdout[-2000:], result.stderr[-2000:]))
        if not (data / "settings.json").is_file() or not (data / "Projects").is_dir():
            raise RuntimeError("The executable did not initialize writable user data")
        print("Packaged Juvion startup OK (disposable user data)")


if __name__ == "__main__":
    main()
