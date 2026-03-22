#!/usr/bin/env python3
"""Foothold Extended Installer / Updater.

Interactive setup for DCS Foothold Extended missions.
Zero external dependencies — stdlib only (AES crypto is optional).

Usage: python setup.py
"""
from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GITHUB_REPO = "BojoteX/Foothold-Extended"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
VERSION_FILE = ".foothold_version"
CONFIG_LUA_PATH = "l10n/DEFAULT/Foothold Config.lua"

ASSET_NAME_RE = re.compile(r"Foothold_Extended_(\w+)_v[\d.]+(?:-\w+)?\.miz")

DISPLAY_NAMES = {
    "Caucasus": "Caucasus",
    "Syria": "Syria",
    "Germany": "Germany",
    "Iraq": "Iraq",
    "Kola": "Kola",
    "PersianGulf": "Persian Gulf",
    "SinaiExtended": "Sinai Extended",
    "SinaiNorth": "Sinai North",
}

ERA_OPTIONS: dict[str, list[str]] = {
    "Caucasus":       ["Modern", "Coldwar"],
    "Syria":          ["Modern", "Coldwar"],
    "Germany":        ["Coldwar"],
    "Iraq":           ["Modern", "Gulfwar"],
    "Kola":           ["Modern", "Coldwar"],
    "Persian Gulf":   ["Modern", "Coldwar"],
    "Sinai Extended": ["Modern", "Coldwar"],
    "Sinai North":    ["Modern", "Coldwar"],
}

ERA_WARNINGS: dict[str, str] = {
    "Kola": "NOTE: Era toggle may not work correctly on Kola.",
}

# Cleanup targets for Ctrl+C
_cleanup_paths: list[Path] = []

# ---------------------------------------------------------------------------
# Terminal helpers — ASCII only, ANSI colors
# ---------------------------------------------------------------------------

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def _enable_ansi():
    """Enable ANSI escape processing on Windows 10+."""
    os.system("")


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def banner():
    print(f"""{CYAN}
  ==========================================================
               FOOTHOLD EXTENDED INSTALLER
  ==========================================================
  {DIM}DCS Multiplayer PvE Campaign by Lekaa{RESET}
  {CYAN}----------------------------------------------------------{RESET}
""")


def step(msg: str):
    print(f"  {CYAN}[*]{RESET} {msg}")


def ok(msg: str):
    print(f"  {GREEN}[+]{RESET} {msg}")


def warn(msg: str):
    print(f"  {YELLOW}[!]{RESET} {msg}")


def error(msg: str):
    print(f"  {RED}[X]{RESET} {msg}")


def info(msg: str):
    print(f"      {msg}")


def section(title: str):
    print()
    print(f"  {BOLD}--- {title} ---{RESET}")
    print()


def press_any_key():
    print()
    print(f"  {DIM}Press any key to exit...{RESET}", end="", flush=True)
    try:
        import msvcrt
        msvcrt.getch()
    except ImportError:
        input()
    print()


# ---------------------------------------------------------------------------
# Arrow-key menus (msvcrt on Windows, fallback to numbered input)
# ---------------------------------------------------------------------------

def _read_key() -> str:
    """Read a keypress. Returns 'up', 'down', 'enter', 'space', 'esc', or char."""
    try:
        import msvcrt
        ch = msvcrt.getch()
        if ch in (b"\xe0", b"\x00"):
            code = msvcrt.getch()
            if code == b"H":
                return "up"
            if code == b"P":
                return "down"
            return ""
        if ch == b"\r":
            return "enter"
        if ch == b" ":
            return "space"
        if ch == b"\x1b":
            return "esc"
        return ch.decode("ascii", errors="replace")
    except ImportError:
        # Non-Windows fallback
        return input().strip() or "enter"


def _draw_options(options: list[str], cursor: int, selected: set[int] | None = None,
                  multi: bool = False):
    """Draw option list. If multi=True, show checkboxes."""
    for i, opt in enumerate(options):
        prefix = ">" if i == cursor else " "
        if multi:
            check = "X" if i in selected else " "
            print(f"    {prefix} [{check}] {opt}")
        else:
            marker = f"{CYAN}>{RESET}" if i == cursor else " "
            highlight = BOLD if i == cursor else ""
            print(f"    {marker} {highlight}{opt}{RESET}")


def select_one(title: str, options: list[str], default: int = 0) -> int:
    """Single-select menu with arrow keys. Returns selected index."""
    print(f"  {title}")
    print()

    cursor = default
    lines_to_clear = len(options) + 2  # options + footer + blank

    _draw_options(options, cursor)
    print()
    print(f"  {DIM}[Up/Down] Navigate  [Enter] Select{RESET}")

    while True:
        key = _read_key()
        if key == "up" and cursor > 0:
            cursor -= 1
        elif key == "down" and cursor < len(options) - 1:
            cursor += 1
        elif key == "enter":
            # Clear menu and show selection
            sys.stdout.write(f"\033[{lines_to_clear}A")
            for _ in range(lines_to_clear):
                print(" " * 60)
            sys.stdout.write(f"\033[{lines_to_clear}A")
            ok(f"{title} {BOLD}{options[cursor]}{RESET}")
            return cursor
        else:
            continue

        # Redraw
        sys.stdout.write(f"\033[{lines_to_clear}A")
        _draw_options(options, cursor)
        print()
        print(f"  {DIM}[Up/Down] Navigate  [Enter] Select{RESET}")


def select_multi(title: str, options: list[str]) -> list[int]:
    """Multi-select menu with arrow keys. Returns list of selected indices."""
    print(f"  {title}")
    print()

    cursor = 0
    selected: set[int] = set()
    lines_to_clear = len(options) + 2

    _draw_options(options, cursor, selected, multi=True)
    print()
    print(f"  {DIM}[Up/Down] Navigate  [Space] Toggle  [Enter] Confirm{RESET}")

    while True:
        key = _read_key()
        if key == "up" and cursor > 0:
            cursor -= 1
        elif key == "down" and cursor < len(options) - 1:
            cursor += 1
        elif key == "space":
            if cursor in selected:
                selected.discard(cursor)
            else:
                selected.add(cursor)
        elif key == "enter":
            if not selected:
                continue  # must select at least one
            sys.stdout.write(f"\033[{lines_to_clear}A")
            for _ in range(lines_to_clear):
                print(" " * 60)
            sys.stdout.write(f"\033[{lines_to_clear}A")
            names = ", ".join(options[i] for i in sorted(selected))
            ok(f"{title} {BOLD}{names}{RESET}")
            return sorted(selected)
        elif key == "esc":
            return []
        else:
            continue

        sys.stdout.write(f"\033[{lines_to_clear}A")
        _draw_options(options, cursor, selected, multi=True)
        print()
        print(f"  {DIM}[Up/Down] Navigate  [Space] Toggle  [Enter] Confirm{RESET}")


# ---------------------------------------------------------------------------
# GitHub API
# ---------------------------------------------------------------------------

def fetch_latest_release() -> dict | None:
    """Fetch latest release from GitHub. Returns parsed JSON or None."""
    step("Checking for latest release...")
    try:
        req = Request(GITHUB_API, headers={"User-Agent": "Foothold-Installer"})
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        ok(f"Latest release: {BOLD}{data.get('tag_name', '?')}{RESET}")
        return data
    except HTTPError as e:
        if e.code == 404:
            error("No releases published yet.")
            info("Ask the server admin to create a release first.")
        elif e.code == 403:
            error("GitHub API rate limit reached.")
            info("Wait a few minutes and try again.")
        else:
            error(f"GitHub API error: HTTP {e.code}")
        return None
    except URLError:
        error("No internet connection.")
        info("Check your network and try again.")
        return None
    except Exception as e:
        error(f"Unexpected error: {e}")
        return None


def get_miz_assets(release: dict) -> list[dict]:
    """Extract .miz assets from release, with display names."""
    assets = []
    for a in release.get("assets", []):
        name = a.get("name", "")
        m = ASSET_NAME_RE.match(name)
        if m:
            raw_theater = m.group(1)
            display = DISPLAY_NAMES.get(raw_theater, raw_theater)
            assets.append({
                "name": name,
                "theater_key": raw_theater,
                "display_name": display,
                "url": a.get("browser_download_url", ""),
                "size": a.get("size", 0),
            })
    return assets


def get_asset_url(release: dict, filename: str) -> str | None:
    """Find a specific asset URL by filename."""
    for a in release.get("assets", []):
        if a.get("name") == filename:
            return a.get("browser_download_url")
    return None


# ---------------------------------------------------------------------------
# Download with progress
# ---------------------------------------------------------------------------

def download_file(url: str, dest: Path, label: str = "") -> bool:
    """Download a file with progress display. Returns True on success."""
    try:
        req = Request(url, headers={
            "User-Agent": "Foothold-Installer",
            "Accept": "application/octet-stream",
        })
        with urlopen(req, timeout=300) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            total_mb = total / (1024 * 1024) if total else 0
            downloaded = 0

            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        mb = downloaded / (1024 * 1024)
                        pct = downloaded * 100 // total
                        sys.stdout.write(
                            f"\r      Downloading {label}... "
                            f"{mb:.1f}/{total_mb:.1f} MB ({pct}%)"
                        )
                        sys.stdout.flush()

            sys.stdout.write("\n")
            return True
    except (URLError, HTTPError, OSError) as e:
        print()
        error(f"Download failed: {e}")
        if dest.exists():
            dest.unlink()
        return False


# ---------------------------------------------------------------------------
# DCS directory detection
# ---------------------------------------------------------------------------

def find_dcs_saved_games() -> list[Path]:
    """Find DCS Saved Games directories that contain a Missions folder."""
    saved_games = Path.home() / "Saved Games"
    if not saved_games.is_dir():
        return []

    candidates = []
    for d in sorted(saved_games.iterdir()):
        if d.is_dir() and d.name.upper().startswith("DCS") and (d / "Missions").is_dir():
            candidates.append(d)
    return candidates


def select_dcs_directory() -> Path | None:
    """Detect and select the DCS Saved Games directory."""
    section("DCS DIRECTORY")

    candidates = find_dcs_saved_games()

    if not candidates:
        error("No DCS Saved Games directory found.")
        info("Expected: C:\\Users\\<you>\\Saved Games\\DCS*\\Missions\\")
        info("Make sure DCS has been run at least once.")
        return None

    if len(candidates) == 1:
        ok(f"Found: {candidates[0].name}")
        return candidates[0]

    # Multiple installs — let user choose
    step("Multiple DCS installs detected:")
    names = [c.name for c in candidates]
    idx = select_one("Select DCS install:", names)
    return candidates[idx]


# ---------------------------------------------------------------------------
# Version management
# ---------------------------------------------------------------------------

def get_installed_theaters(missions_dir: Path) -> dict[str, str]:
    """Scan for installed Foothold theaters and their versions."""
    installed = {}
    for d in missions_dir.iterdir():
        if d.is_dir() and d.name.startswith("Foothold Extended - "):
            theater = d.name.replace("Foothold Extended - ", "")
            ver_file = d / VERSION_FILE
            if ver_file.is_file():
                installed[theater] = ver_file.read_text().strip()
            else:
                installed[theater] = "unknown"
    return installed


# ---------------------------------------------------------------------------
# Era configuration
# ---------------------------------------------------------------------------

def select_era(theater_name: str) -> str:
    """Select era for a theater. Returns era string."""
    options = ERA_OPTIONS.get(theater_name, ["Modern", "Coldwar"])

    if len(options) == 1:
        ok(f"{theater_name}: {options[0]} (only option)")
        return options[0]

    idx = select_one(f"Era for {theater_name}:", options)

    warning = ERA_WARNINGS.get(theater_name)
    if warning:
        warn(warning)

    return options[idx]


# ---------------------------------------------------------------------------
# DCS WebGUI API (localhost only, port 8088)
# ---------------------------------------------------------------------------

DCS_API_URL = "http://127.0.0.1:8088/encryptedRequest"
DCS_API_KEY = hashlib.sha256(b"DigitalCombatSimulator.com").digest()

_has_crypto = False
try:
    from Crypto.Cipher import AES as _AES
    from Crypto.Util.Padding import pad as _pad, unpad as _unpad
    _has_crypto = True
except ImportError:
    pass


def _dcs_api(action: str, params: dict | None = None) -> any:
    """Call a DCS WebGUI API action. Returns parsed response or None on error.
    Requires pycryptodome. Returns None silently if not available."""
    if not _has_crypto:
        return None
    try:
        iv = os.urandom(16)
        body = {"uri": action}
        if params:
            body.update(params)
        cipher = _AES.new(DCS_API_KEY, _AES.MODE_CBC, iv)
        ct = cipher.encrypt(_pad(json.dumps(body).encode(), _AES.block_size))
        req_body = json.dumps({
            "ct": base64.b64encode(ct).decode(),
            "iv": base64.b64encode(iv).decode(),
        })
        req = Request(DCS_API_URL,
                      data=req_body.encode("utf-8"),
                      headers={"Content-Type": "application/json"})
        resp = urlopen(req, timeout=5)
        data = json.loads(resp.read())
        rcipher = _AES.new(DCS_API_KEY, _AES.MODE_CBC,
                           base64.b64decode(data["iv"]))
        plain = _unpad(rcipher.decrypt(base64.b64decode(data["ct"])),
                       _AES.block_size)
        return json.loads(plain.decode())
    except Exception:
        return None


def is_dcs_server_running() -> bool:
    """Check if DCS server process is running."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq DCS_server.exe", "/FO", "CSV"],
            capture_output=True, text=True, timeout=5,
        )
        return "DCS_server.exe" in result.stdout
    except Exception:
        return False


def is_dcs_mission_running() -> bool:
    """Check if a mission is actively running via WebGUI API."""
    mode = _dcs_api("getSimulatorMode")
    return mode is not None and mode > 1


def stop_dcs_gracefully() -> bool:
    """Gracefully stop DCS server via WebGUI API. Returns True if stopped."""
    if not is_dcs_server_running():
        return True

    if not _has_crypto:
        warn("Cannot stop DCS gracefully (pycryptodome not installed).")
        info("Please stop the server manually via the WebGUI.")
        return False

    # Try graceful stop via API
    _dcs_api("stopServer")
    time.sleep(2)

    # Verify mission stopped
    mode = _dcs_api("getSimulatorMode")
    if mode is not None and mode <= 1:
        return True

    # If API didn't work, mission may not be loaded
    if mode is None and is_dcs_server_running():
        warn("DCS is running but WebGUI API is not responding.")
        info("Please stop the server manually.")
        return False

    return True


def start_dcs_mission() -> bool:
    """Start the mission via WebGUI API (DCS process must already be running).
    Uses startServer which re-reads serverSettings.lua from disk to pick up
    the new .miz path. Falls back to launching the DCS process if not running."""
    if is_dcs_server_running():
        # DCS is in lobby mode — use startServer to reload settings from disk
        # Wait a moment for DCS to fully settle in lobby after stopServer
        time.sleep(3)
        result = _dcs_api("startServer", {"listStartIndex": 1})
        if result is not None:
            time.sleep(5)
            mode = _dcs_api("getSimulatorMode")
            return mode is not None and mode > 1
        return False

    # DCS process not running — launch it
    dcs_exe = Path(r"C:\Program Files\Eagle Dynamics\DCS World Server\bin\DCS_server.exe")
    if not dcs_exe.is_file():
        install = find_dcs_install()
        if install:
            dcs_exe = install / "bin" / "DCS_server.exe"
    if not dcs_exe.is_file():
        return False
    try:
        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen([str(dcs_exe)], creationflags=CREATE_NO_WINDOW)
        time.sleep(3)
        return is_dcs_server_running()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# MissionScripting.lua desanitization
# ---------------------------------------------------------------------------

SANITIZE_TARGETS = [
    "sanitizeModule('io')",
    "sanitizeModule('lfs')",
    "_G['require'] = nil",
    "_G['package'] = nil",
]


def find_dcs_install() -> Path | None:
    """Find DCS installation directory via registry or common paths."""
    # Try registry (works for both client and server installs)
    if os.name == "nt":
        try:
            import winreg
            for hive in (winreg.HKEY_LOCAL_MACHINE, ):
                for view in (winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
                             winreg.KEY_READ | winreg.KEY_WOW64_32KEY):
                    try:
                        key = winreg.OpenKey(
                            hive,
                            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                            0, view,
                        )
                        i = 0
                        while True:
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                subkey = winreg.OpenKey(key, subkey_name, 0, view)
                                try:
                                    name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                    if "DCS World" in name:
                                        loc = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                                        p = Path(loc)
                                        ms = p / "Scripts" / "MissionScripting.lua"
                                        if ms.is_file():
                                            return p
                                except (OSError, FileNotFoundError):
                                    pass
                                finally:
                                    winreg.CloseKey(subkey)
                                i += 1
                            except OSError:
                                break
                        winreg.CloseKey(key)
                    except OSError:
                        continue
        except ImportError:
            pass

    # Fallback: common paths
    for candidate in [
        Path(r"C:\Program Files\Eagle Dynamics\DCS World"),
        Path(r"C:\Program Files\Eagle Dynamics\DCS World Server"),
        Path(r"C:\Program Files\Eagle Dynamics\DCS World OpenBeta"),
    ]:
        ms = candidate / "Scripts" / "MissionScripting.lua"
        if ms.is_file():
            return candidate

    return None


def check_mission_scripting(dcs_install: Path) -> bool:
    """Check if MissionScripting.lua is already desanitized. Returns True if OK."""
    ms_path = dcs_install / "Scripts" / "MissionScripting.lua"
    if not ms_path.is_file():
        return False

    text = ms_path.read_text(encoding="utf-8", errors="replace")
    for target in SANITIZE_TARGETS:
        # If the line exists and is NOT commented out, it needs fixing
        for line in text.splitlines():
            stripped = line.strip()
            if stripped == target:
                return False
    return True


def desanitize_mission_scripting(dcs_install: Path) -> bool:
    """Desanitize MissionScripting.lua. Returns True on success."""
    ms_path = dcs_install / "Scripts" / "MissionScripting.lua"

    # Check if we can write directly
    try:
        text = ms_path.read_text(encoding="utf-8", errors="replace")
        new_lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped in SANITIZE_TARGETS:
                new_lines.append("\t--" + stripped)
            else:
                new_lines.append(line)
        new_text = "\n".join(new_lines) + "\n"

        try:
            ms_path.write_text(new_text, encoding="utf-8")
            return True
        except PermissionError:
            pass

        # Need admin elevation — write to temp file and use PowerShell
        if os.name == "nt":
            tmp = Path(tempfile.mktemp(suffix=".lua", prefix="ms_"))
            tmp.write_text(new_text, encoding="utf-8")

            # Build a script block to avoid nested quoting issues
            ps_script = tmp.with_suffix(".ps1")
            ps_script.write_text(
                f'Copy-Item -Path "{tmp}" -Destination "{ms_path}" -Force\n'
                f'Remove-Item -Path "{tmp}" -Force\n'
                f'Remove-Item -Path "{ps_script}" -Force\n',
                encoding="utf-8",
            )

            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f'Start-Process powershell -Verb RunAs -Wait -ArgumentList '
                 f"'-NoProfile -ExecutionPolicy Bypass -File \"{ps_script}\"'"],
                capture_output=True, timeout=30,
            )
            # Clean up if elevation was denied or failed
            if tmp.exists():
                tmp.unlink()
            if ps_script.exists():
                ps_script.unlink()

            # Verify the change took effect
            return check_mission_scripting(dcs_install)

    except Exception as e:
        warn(f"Failed to update MissionScripting.lua: {e}")
        return False

    return False


# ---------------------------------------------------------------------------
# Installation
# ---------------------------------------------------------------------------

def extract_config_to_saves(miz_path: Path, saves_dir: Path, era: str) -> bool:
    """Extract Foothold Config.lua from .miz and place in Missions/Saves/.
    Sets the era in the extracted config. Returns True on success."""
    saves_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(miz_path, "r") as zf:
            if CONFIG_LUA_PATH not in zf.namelist():
                warn("Foothold Config.lua not found in .miz")
                return False

            config_data = zf.read(CONFIG_LUA_PATH).decode("utf-8", errors="replace")

        # Set the era in the extracted config
        new_config = re.sub(
            r'(Era\s*=\s*)"[^"]*"',
            rf'\1"{era}"',
            config_data,
            count=1,
        )

        config_dest = saves_dir / "Foothold Config.lua"
        config_dest.write_text(new_config, encoding="utf-8")
        return True
    except Exception as e:
        warn(f"Config extraction failed: {e}")
        return False


def update_server_mission_list(dcs_dir: Path, miz_path: Path,
                               theater_display: str) -> bool:
    """Update serverSettings.lua mission list to point to the new .miz file.
    Replaces any existing Foothold Extended entry for this theater, or adds one."""
    settings_path = dcs_dir / "Config" / "serverSettings.lua"
    if not settings_path.is_file():
        return False

    try:
        text = settings_path.read_text(encoding="utf-8", errors="replace")
        miz_lua_path = str(miz_path).replace("\\", "\\\\")

        # Pattern: a line inside missionList containing this theater's folder
        folder_escaped = re.escape(f"Foothold Extended - {theater_display}")
        pattern = re.compile(
            r'(\[\d+\]\s*=\s*").*?' + folder_escaped + r'.*?(")',
            re.DOTALL,
        )

        match = pattern.search(text)
        if match:
            # Replace existing entry with new path
            new_text = text[:match.start()] + f'[1] = "{miz_lua_path}"' + text[match.end():]
            settings_path.write_text(new_text, encoding="utf-8")
            return True
        else:
            # No existing entry -- add to mission list
            ml_match = re.search(
                r'(\["missionList"\]\s*=\s*\n?\s*\{)',
                text,
            )
            if ml_match:
                insert_pos = ml_match.end()
                entry = f'\n\t\t[1] = "{miz_lua_path}",'
                new_text = text[:insert_pos] + entry + text[insert_pos:]
                settings_path.write_text(new_text, encoding="utf-8")
                return True

        return False
    except Exception:
        return False


def rename_miz_with_era(miz_path: Path, era: str) -> Path:
    """Rename .miz file to include era. Returns new path."""
    stem = miz_path.stem  # e.g. Foothold_Extended_Caucasus_v1.0.0
    new_name = f"{stem}_{era}.miz"
    new_path = miz_path.parent / new_name
    miz_path.rename(new_path)
    return new_path


def install_theater(
    missions_dir: Path,
    theater_display: str,
    miz_url: str,
    miz_filename: str,
    briefing_url: str | None,
    version: str,
    era: str,
) -> bool:
    """Install a single theater. Always a clean install."""
    install_dir = missions_dir / f"Foothold Extended - {theater_display}"

    # Clean install -- kill any running watchers first, then remove
    if install_dir.exists():
        step(f"Removing previous install...")
        # Stop any running briefing.pyw watchers that lock the directory
        pyw_path = install_dir / "briefing.pyw"
        if pyw_path.is_file():
            try:
                subprocess.run(
                    [sys.executable, str(pyw_path), "--stop"],
                    capture_output=True, timeout=5,
                )
            except Exception:
                pass
        shutil.rmtree(install_dir, ignore_errors=True)

    install_dir.mkdir(parents=True, exist_ok=True)
    _cleanup_paths.append(install_dir)

    # Download .miz
    miz_dest = install_dir / miz_filename
    if not download_file(miz_url, miz_dest, miz_filename):
        error(f"Failed to download {miz_filename}")
        shutil.rmtree(install_dir, ignore_errors=True)
        return False

    # Download briefing.pyw
    if briefing_url:
        pyw_dest = install_dir / "briefing.pyw"
        if not download_file(briefing_url, pyw_dest, "briefing.pyw"):
            warn("briefing.pyw download failed -- continuing without it.")

    # Rename .miz to include era
    step(f"Configuring for {era} era...")
    miz_dest = rename_miz_with_era(miz_dest, era)
    ok(f"Mission file: {miz_dest.name}")

    # Update serverSettings.lua to point to the new .miz
    dcs_dir = missions_dir.parent  # Saved Games/DCS.xxx
    if update_server_mission_list(dcs_dir, miz_dest, theater_display):
        ok("Server mission list updated.")
    else:
        warn("Could not update serverSettings.lua -- load mission via WebGUI.")

    # Extract Foothold Config.lua to Missions/Saves/ with era set
    saves_dir = missions_dir / "Saves"
    if extract_config_to_saves(miz_dest, saves_dir, era):
        ok(f"Config deployed to Missions/Saves/Foothold Config.lua")
    else:
        warn("Could not extract config -- you may need to set era manually.")

    # Write version
    (install_dir / VERSION_FILE).write_text(version)

    _cleanup_paths.remove(install_dir)
    return True


def verify_install(missions_dir: Path, theater_display: str) -> bool:
    """Verify a theater installation."""
    install_dir = missions_dir / f"Foothold Extended - {theater_display}"

    # Find the .miz file
    miz_files = list(install_dir.glob("*.miz"))
    if not miz_files:
        error(f"No .miz file found in {install_dir.name}")
        return False

    miz = miz_files[0]
    if not zipfile.is_zipfile(miz):
        error(f"{miz.name} is not a valid archive")
        return False

    with zipfile.ZipFile(miz, "r") as zf:
        if CONFIG_LUA_PATH not in zf.namelist():
            warn(f"{miz.name} missing {CONFIG_LUA_PATH}")

    if not (install_dir / VERSION_FILE).is_file():
        warn("Version file missing")

    return True


# ---------------------------------------------------------------------------
# Signal handler
# ---------------------------------------------------------------------------

def _on_interrupt(sig, frame):
    print()
    warn("Installation cancelled.")
    for p in _cleanup_paths:
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def status_banner(choices: dict):
    """Show a compact status bar of selections made so far."""
    if not choices:
        return
    print(f"  {DIM}----------------------------------------------------------{RESET}")
    for label, value in choices.items():
        print(f"  {DIM}{label}:{RESET} {BOLD}{value}{RESET}")
    print(f"  {DIM}----------------------------------------------------------{RESET}")
    print()


def main():
    _enable_ansi()
    signal.signal(signal.SIGINT, _on_interrupt)

    # Track user selections for status display
    choices: dict[str, str] = {}

    # ── Step 1: Detect DCS ──────────────────────────────────────
    clear()
    banner()

    dcs_dir = select_dcs_directory()
    if not dcs_dir:
        press_any_key()
        sys.exit(1)

    missions_dir = dcs_dir / "Missions"
    choices["DCS Directory"] = dcs_dir.name

    # ── Step 2: Check MissionScripting.lua (silent, no user input) ──
    dcs_install = find_dcs_install()
    ms_status = "N/A"
    if dcs_install:
        if check_mission_scripting(dcs_install):
            ms_status = "OK"
        else:
            step("Updating MissionScripting.lua (may request admin access)...")
            if desanitize_mission_scripting(dcs_install):
                ms_status = "Updated"
            else:
                ms_status = "MANUAL FIX NEEDED"
    choices["MissionScripting"] = ms_status

    # ── Step 3: Fetch release (silent, no user input) ───────────
    clear()
    banner()
    status_banner(choices)
    step("Checking for latest release...")

    release = fetch_latest_release()
    if not release:
        press_any_key()
        sys.exit(1)

    latest_version = release.get("tag_name", "unknown")
    miz_assets = get_miz_assets(release)
    briefing_url = get_asset_url(release, "briefing.pyw")

    if not miz_assets:
        error("No .miz files found in the latest release.")
        press_any_key()
        sys.exit(1)

    choices["Latest Version"] = latest_version

    # Show installed status if any
    installed = get_installed_theaters(missions_dir)
    if installed:
        print()
        for theater, ver in sorted(installed.items()):
            if ver == latest_version:
                status = f"{GREEN}UP TO DATE{RESET}"
            elif ver == "unknown":
                status = f"{YELLOW}UNKNOWN{RESET}"
            else:
                status = f"{YELLOW}{ver} -> {latest_version}{RESET}"
            info(f"Installed: {theater} [{status}]")

    # ── Step 4: Select theater ──────────────────────────────────
    clear()
    banner()
    status_banner(choices)

    theater_names = [a["display_name"] for a in miz_assets]
    selected_idx = select_one("Select theater to install:", theater_names)
    asset = miz_assets[selected_idx]
    theater_name = asset["display_name"]
    choices["Theater"] = theater_name

    # ── Step 5: Select era ──────────────────────────────────────
    clear()
    banner()
    status_banner(choices)

    era = select_era(theater_name)
    choices["Era"] = era

    # ── Step 6: Confirm ─────────────────────────────────────────
    clear()
    banner()
    status_banner(choices)

    size_mb = asset["size"] / (1024 * 1024)
    info(f"Download: {size_mb:.1f} MB")
    print()

    if ms_status == "MANUAL FIX NEEDED":
        warn("MissionScripting.lua needs manual desanitization.")
        info(f"  Edit: {dcs_install / 'Scripts' / 'MissionScripting.lua'}")
        info("  Comment out sanitizeModule lines for io, lfs,")
        info("  and _G['require'] / _G['package'] lines.")
        print()

    step("Press [Enter] to install or [Esc] to cancel.")
    key = _read_key()
    if key != "enter":
        warn("Cancelled.")
        press_any_key()
        sys.exit(0)

    # ── Step 7: Stop server if running ──────────────────────────
    clear()
    banner()
    status_banner(choices)

    server_was_running = False
    if is_dcs_server_running():
        step("DCS server is running. Stopping gracefully...")
        if stop_dcs_gracefully():
            ok("Server stopped.")
            server_was_running = True
        else:
            error("Could not stop the server.")
            info("Stop the server manually, then run setup again.")
            press_any_key()
            sys.exit(1)

    # ── Step 8: Install ─────────────────────────────────────────
    success = install_theater(
        missions_dir=missions_dir,
        theater_display=theater_name,
        miz_url=asset["url"],
        miz_filename=asset["name"],
        briefing_url=briefing_url,
        version=latest_version,
        era=era,
    )

    if not success:
        error(f"{theater_name} installation failed.")
        if server_was_running:
            step("Restarting server...")
            start_dcs_mission()
        press_any_key()
        sys.exit(1)

    verified = verify_install(missions_dir, theater_name)
    if verified:
        ok(f"{theater_name} installed and verified.")
    else:
        warn(f"{theater_name} installed with warnings.")

    # Restart server if it was running before
    if server_was_running:
        step("Restarting DCS server...")
        if start_dcs_mission():
            ok("Server restarted.")
        else:
            warn("Could not restart server automatically.")
            info("Start it manually via the DCS WebGUI or shortcut.")

    # Generate kneeboard
    install_dir = missions_dir / f"Foothold Extended - {theater_name}"
    pyw_path = install_dir / "briefing.pyw"
    if pyw_path.is_file():
        step("Generating kneeboard briefing...")
        try:
            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen(
                ["pythonw", str(pyw_path)],
                cwd=str(install_dir),
                creationflags=CREATE_NO_WINDOW,
            )
            ok("Kneeboard generated and watcher started.")
        except Exception as e:
            warn(f"Could not launch briefing: {e}")
            info("You can start it manually by double-clicking briefing.pyw")

    # ── Step 8: Final summary ───────────────────────────────────
    clear()
    banner()

    print(f"  {GREEN}==========================================================")
    print(f"                    INSTALLATION COMPLETE")
    print(f"  =========================================================={RESET}")
    print()
    info(f"Theater:  {BOLD}{theater_name}{RESET}")
    info(f"Era:      {BOLD}{era}{RESET}")
    info(f"Version:  {BOLD}{latest_version}{RESET}")
    info(f"DCS:      {dcs_dir.name}")
    info(f"Location: {install_dir}")
    print()
    print(f"  {BOLD}NEXT STEPS:{RESET}")
    info("  1. Load the mission via the DCS WebGUI or Mission Editor")
    info("  2. The kneeboard briefing has been generated automatically")
    info("  3. Double-click briefing.pyw anytime to regenerate kneeboards")
    print()
    saves_dir = missions_dir / "Saves"
    print(f"  {BOLD}ADVANCED SETTINGS:{RESET}")
    info(f"  Edit: {saves_dir / 'Foothold Config.lua'}")
    info("  Change difficulty, AI behavior, shop items, and more.")
    info("  See the Foothold manual for all available options.")

    press_any_key()


if __name__ == "__main__":
    main()
