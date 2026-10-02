#!/usr/bin/env python3
"""
Universal Cross-Platform Packaging Script for Juvion.
Supports Windows (.exe / .zip / Inno Setup), Linux (.tar.gz / AppImage), and macOS (.app / .dmg).
"""

import sys
import os
import shutil
import subprocess
import platform
import argparse
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
APP_VERSION = json.loads((BASE_DIR / "version.json").read_text(encoding="utf-8"))["version"]


def target_architecture():
    machine = platform.machine().lower()
    return {"amd64": "x86_64", "aarch64": "arm64"}.get(machine, machine)

def get_python_executable():
    """Detect appropriate Python executable (venv preferred)."""
    venv_win = BASE_DIR / "venv" / "Scripts" / "python.exe"
    venv_posix = BASE_DIR / "venv" / "bin" / "python3"
    dot_venv_win = BASE_DIR / ".venv" / "Scripts" / "python.exe"
    dot_venv_posix = BASE_DIR / ".venv" / "bin" / "python3"

    candidates = [venv_win, dot_venv_win] if os.name == "nt" else [venv_posix, dot_venv_posix]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable

def run_command(cmd, cwd=None):
    """Run shell command with streaming output and error checking."""
    print(f"\n--> Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    res = subprocess.run(cmd, cwd=cwd or BASE_DIR, shell=isinstance(cmd, str))
    if res.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {res.returncode}")

def check_pyinstaller(python_exe):
    """Ensure PyInstaller is installed."""
    try:
        subprocess.run([python_exe, "-m", "PyInstaller", "--version"], check=True, capture_output=True)
        print("[OK] PyInstaller is available.")
    except Exception:
        print("[*] Installing PyInstaller...")
        run_command([python_exe, "-m", "pip", "install", "pyinstaller"])

def build_pyinstaller(python_exe, dist_dir=None):
    """Execute PyInstaller with juvion.spec."""
    print("\n[+] Compiling Juvion with PyInstaller...")
    spec_file = BASE_DIR / "juvion.spec"
    if not spec_file.exists():
        raise FileNotFoundError(f"Missing spec file: {spec_file}")
    command = [python_exe, "-m", "PyInstaller", str(spec_file), "--noconfirm", "--clean"]
    if dist_dir is not None:
        command += ["--distpath", str(dist_dir)]
    run_command(command)

def package_windows(dist_dir=None):
    """Package for Windows: ZIP and Inno Setup installer."""
    dist_dir = Path(dist_dir or BASE_DIR / "dist").resolve()
    app_dir = dist_dir / "Juvion"
    if not app_dir.exists():
        raise FileNotFoundError(f"Missing build: {app_dir}")

    # 1. Create portable zip
    zip_path = dist_dir / f"Juvion_v{APP_VERSION}_Windows_Portable.zip"
    print(f"\n[+] Creating portable zip: {zip_path.name}...")
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", root_dir=dist_dir, base_dir="Juvion")
    print(f"[OK] Created: {zip_path}")

    # 2. Check for Inno Setup compiler
    iscc_candidates = [
        shutil.which("iscc"),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
    ]
    iscc = next((c for c in iscc_candidates if c and os.path.exists(c)), None)

    if iscc:
        print(f"\n[+] Building Windows Setup Wizard using Inno Setup ({iscc})...")
        iss_file = BASE_DIR / "installer_windows.iss"
        run_command([iscc, f"/DMyAppVersion={APP_VERSION}", f"/DMyAppSourceDir={app_dir}", f"/DMyAppOutputDir={dist_dir / 'installer'}", str(iss_file)])
        print("[OK] Windows installer created in dist/installer/")
    else:
        print("\n[INFO] Inno Setup compiler (ISCC.exe) not found.")
        print("       - Portable build is ready in: dist/Juvion/")
        print(f"       - Portable zip is ready at: {zip_path}")
        print("       - To generate the .exe Setup Wizard, install Inno Setup 6:")
        print("         https://jrsoftware.org/isdl.php")
        print("         Then run: ISCC.exe installer_windows.iss")

def package_linux(dist_dir=None):
    """Package for Linux: tar.gz and AppDir."""
    dist_dir = Path(dist_dir or BASE_DIR / "dist").resolve()
    app_dir = dist_dir / "Juvion"
    if not app_dir.exists():
        raise FileNotFoundError(f"Missing build: {app_dir}")

    architecture = target_architecture()
    tar_path = dist_dir / f"Juvion-v{APP_VERSION}-linux-{architecture}.tar.gz"
    print(f"\n[+] Creating tar.gz archive: {tar_path.name}...")
    shutil.make_archive(str(tar_path).removesuffix(".tar.gz"), "gztar", root_dir=dist_dir, base_dir="Juvion")
    print(f"[OK] Created: {tar_path}")

    # Prepare AppDir
    appdir = dist_dir / "Juvion.AppDir"
    usr_bin = appdir / "usr" / "bin"
    apps_dir = appdir / "usr" / "share" / "applications"
    icons_dir = appdir / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps"

    usr_bin.mkdir(parents=True, exist_ok=True)
    apps_dir.mkdir(parents=True, exist_ok=True)
    icons_dir.mkdir(parents=True, exist_ok=True)

    shutil.copytree(app_dir, usr_bin, dirs_exist_ok=True)

    desktop_src = BASE_DIR / "assets" / "juvion.desktop"
    if desktop_src.exists():
        shutil.copy(desktop_src, apps_dir / "juvion.desktop")
        shutil.copy(desktop_src, appdir / "juvion.desktop")

    icon_src = BASE_DIR / "assets" / "icons" / "app_icon.png"
    if icon_src.exists():
        shutil.copy(icon_src, icons_dir / "juvion.png")
        shutil.copy(icon_src, appdir / "juvion.png")

    apprun = appdir / "AppRun"
    with open(apprun, "w", encoding="utf-8") as f:
        f.write("#!/bin/sh\nAPPDIR=\"$(dirname \"$(readlink -f \"$0\")\")\"\nexport PATH=\"$APPDIR/usr/bin:$PATH\"\nexport LD_LIBRARY_PATH=\"$APPDIR/usr/bin:$APPDIR/usr/lib:$LD_LIBRARY_PATH\"\ncd \"$APPDIR/usr/bin\"\nexec ./Juvion \"$@\"\n")
    os.chmod(apprun, 0o755)
    print(f"[OK] AppDir prepared at {appdir}")

    # Check for appimagetool
    if shutil.which("appimagetool"):
        print("[+] Creating AppImage...")
        env = os.environ.copy()
        env["ARCH"] = "aarch64" if architecture == "arm64" else architecture
        subprocess.run(["appimagetool", str(appdir), str(dist_dir / f"Juvion-{architecture}.AppImage")], env=env, check=True)
        print("[OK] AppImage created in dist/Juvion-x86_64.AppImage")

def package_macos(dist_dir=None):
    """Package for macOS: ad-hoc codesign and DMG image."""
    dist_dir = Path(dist_dir or BASE_DIR / "dist").resolve()
    app_bundle = dist_dir / "Juvion.app"
    if not app_bundle.exists():
        raise FileNotFoundError(f"Missing build: {app_bundle}")

    identity = os.environ.get("JUVION_CODESIGN_IDENTITY", "-")
    print(f"\n[+] Signing Juvion.app ({identity})...")
    signing = ["codesign", "--force", "--deep", "--sign", identity]
    if identity != "-":
        signing += ["--options", "runtime", "--timestamp"]
    run_command(signing + [str(app_bundle)])

    if shutil.which("hdiutil"):
        print("[+] Generating DMG image...")
        dmg_tmp = dist_dir / "dmg_tmp"
        dmg_tmp.mkdir(exist_ok=True)
        shutil.copytree(app_bundle, dmg_tmp / "Juvion.app", dirs_exist_ok=True)

        apps_link = dmg_tmp / "Applications"
        if not apps_link.exists():
            os.symlink("/Applications", apps_link)

        dmg_out = dist_dir / "Juvion.dmg"
        if dmg_out.exists():
            dmg_out.unlink()

        run_command(["hdiutil", "create", "-volname", "Juvion", "-srcfolder", str(dmg_tmp), "-ov", "-format", "UDZO", str(dmg_out)])
        profile = os.environ.get("JUVION_NOTARY_PROFILE")
        if profile:
            run_command(["xcrun", "notarytool", "submit", str(dmg_out), "--keychain-profile", profile, "--wait"])
            run_command(["xcrun", "stapler", "staple", str(dmg_out)])
        shutil.rmtree(dmg_tmp, ignore_errors=True)
        print(f"[OK] DMG installer created at {dmg_out}")

def main():
    parser = argparse.ArgumentParser(description="Build and package Juvion cross-platform")
    parser.add_argument("--skip-build", action="store_true", help="Skip PyInstaller compilation and only run packaging")
    parser.add_argument("--install-dependencies", action="store_true", help="Install requirements into the selected build environment")
    parser.add_argument("--dist-dir", type=Path, default=BASE_DIR / "dist", help="Output directory for builds and packages")
    parser.add_argument("--platform", choices=["auto", "windows", "linux", "darwin"], default="auto", help="Target OS packaging")
    args = parser.parse_args()

    current_os = platform.system().lower()
    target_os = current_os if args.platform == "auto" else args.platform
    if target_os != current_os:
        parser.error("Build each package on its target operating system; PyInstaller does not cross-compile.")

    print("=================================================")
    print(f"   JUVION — Universal Packaging Pipeline")
    print(f"   Host OS:   {platform.system()} ({platform.machine()})")
    print(f"   Target:    {target_os.capitalize()}")
    print("=================================================")

    python_exe = get_python_executable()
    print(f"Python: {python_exe}")
    if args.install_dependencies:
        run_command([python_exe, "-m", "pip", "install", "-r", str(BASE_DIR / "requirements.txt")])

    if not args.skip_build:
        check_pyinstaller(python_exe)
        build_pyinstaller(python_exe, args.dist_dir)

    if target_os == "windows":
        package_windows(args.dist_dir)
    elif target_os == "linux":
        package_linux(args.dist_dir)
    elif target_os in ("darwin", "macos"):
        package_macos(args.dist_dir)

    print("\n=================================================")
    print("   Packaging workflow finished!")
    print("=================================================")

if __name__ == "__main__":
    main()
