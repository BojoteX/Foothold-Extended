#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Auto-install dependencies if missing
def _ensure_deps():
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("Pillow not found. Installing...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "Pillow"],
            stdout=subprocess.DEVNULL,
        )
        print("Pillow installed.")

_ensure_deps()

from PIL import Image, ImageDraw, ImageFont

# Double-click friendly
os.chdir(Path(__file__).resolve().parent)

# When run as .pyw (pythonw.exe), stdout/stderr are None — redirect to devnull
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")


# ----------------------------- Config -----------------------------

IMG_W, IMG_H = 768, 1024
PAD = 18
CARD_PAD = 10
CARD_RAD = 8
COL_GAP = 10

BG        = (11, 18, 32)
CARD_BG   = (17, 27, 46)
CARD_BORDER = (34, 48, 85)
TEXT      = (230, 238, 252)
MUTED     = (168, 182, 216)
BLUE      = (58, 160, 255)
RED       = (255, 77, 90)
AMBER     = (255, 204, 102)
GREEN     = (77, 227, 138)

PILL_COLORS = {
    "SEAD": AMBER, "STRIKE": AMBER, "ATTACK": RED,
    "SUPPORT": GREEN, "CAPTURE": BLUE, "INFO": BLUE,
}

INFRA_NAMES: Set[str] = {
    "MiningFacility", "TankFactory", "FuelDepo", "ArtilleryFactory",
    "ChemSite", "SecretTechFacility", "InsurgentCamp", "AmmonitionDepo",
}
SAVE_NAME_WHITELIST_RE = re.compile(r"^FootHold_.*\.lua$", re.IGNORECASE)
THREAT_KEYWORDS = (
    "SA-", "S-300", "S-200", "Patriot", "HAWK", "NASAMS", "IRIS", "Tor", "Osa",
    "Buk", "Kub", "Strela", "Tunguska", "Pantsir", "Shilka", "ZU-", "AAA", "EWR", "Radar"
)

def is_sam_zone_name(name: str) -> bool:
    return name.startswith("SAM-") or name == "SAMSite"


# ----------------------------- Fonts -----------------------------

def _try_font(name: str, size: int) -> Optional[ImageFont.FreeTypeFont]:
    try:
        return ImageFont.truetype(name, size)
    except (OSError, IOError):
        return None

def load_fonts():
    # Try Windows system fonts, then common paths, then fallback
    search = {
        "regular": ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"],
        "bold":    ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"],
        "mono":    ["consola.ttf", "cour.ttf", "DejaVuSansMono.ttf"],
    }
    fonts = {}
    for key, candidates in search.items():
        found = None
        for c in candidates:
            found = _try_font(c, 12)
            if found:
                fonts[key] = c
                break
        if not found:
            fonts[key] = None
    return fonts

_FONT_NAMES = load_fonts()

def font(style: str, size: int) -> ImageFont.FreeTypeFont:
    name = _FONT_NAMES.get(style)
    if name:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            pass
    return ImageFont.load_default()


# ----------------------------- Helpers: encoding / time / coords -----------------------------

def decode_any(raw: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "utf-16"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("latin-1", errors="replace")

def fmt_time_block(generated_utc: str) -> str:
    try:
        dt = datetime.fromisoformat(generated_utc.replace("Z", "+00:00"))
        utc = dt.astimezone(timezone.utc).strftime("%d%H%MZ %b %Y")
        return f"TIME: {utc}"
    except Exception:
        return "TIME: N/A"

def deg_to_dm(deg: float, is_lat: bool) -> str:
    hemi = ("N" if deg >= 0 else "S") if is_lat else ("E" if deg >= 0 else "W")
    v = abs(deg)
    d = int(v)
    m = (v - d) * 60.0
    if is_lat:
        return f"{hemi} {d:02d}\u00b0{m:06.3f}'"
    return f"{hemi} {d:03d}\u00b0{m:06.3f}'"

def format_latlon(lat: Optional[float], lon: Optional[float]) -> str:
    if lat is None or lon is None:
        return ""
    return f"{deg_to_dm(lat, True)} {deg_to_dm(lon, False)}"


# ----------------------------- Locate single miz -----------------------------

def find_single_miz(cwd: Path) -> Path:
    miz_files = sorted([p for p in cwd.glob("*.miz") if p.is_file()], key=lambda p: p.name.lower())
    if len(miz_files) == 0:
        raise SystemExit(
            "ERROR: No .miz file found in the current directory.\n"
            "Foothold should be in its own folder with exactly one .miz.\n"
            "Fix: Move this script into the Foothold mission folder and run again."
        )
    if len(miz_files) > 1:
        names = "\n".join(f" - {p.name}" for p in miz_files)
        raise SystemExit(
            "ERROR: Multiple .miz files found in the current directory.\n"
            "Foothold should be a single .miz file in its own directory.\n\n"
            f"Found:\n{names}\n\n"
            "Fix: Keep only the Foothold .miz in this folder and run again."
        )
    return miz_files[0].resolve()


# ----------------------------- Directory-mode extraction -----------------------------

def extract_setup_lua_from_dir(theater_dir: Path) -> Tuple[str, str]:
    """Read the setup script directly from an unpacked theater directory."""
    l10n = theater_dir / "l10n" / "DEFAULT"
    if not l10n.is_dir():
        raise FileNotFoundError(f"No l10n/DEFAULT/ found in {theater_dir}")

    lua_files = sorted(l10n.glob("*.lua"), key=lambda p: p.name.lower())
    if not lua_files:
        raise FileNotFoundError(f"No .lua files found in {l10n}")

    def score(p: Path) -> Tuple[int, int]:
        ln = p.name.lower()
        if "ma_setup" in ln:
            s = 3
        elif "setup" in ln:
            s = 2
        else:
            s = 1
        return (-s, len(p.name))

    lua_files.sort(key=score)
    for cand in lua_files:
        text = decode_any(cand.read_bytes())
        if "bc:addConnection" in text:
            return text, cand.name
    best = lua_files[0]
    return decode_any(best.read_bytes()), best.name

def extract_zonecommander_from_dir(theater_dir: Path) -> Tuple[Optional[str], Optional[str]]:
    """Read zoneCommander.lua directly from an unpacked theater directory."""
    l10n = theater_dir / "l10n" / "DEFAULT"
    if not l10n.is_dir():
        return None, None

    for f in l10n.iterdir():
        if f.name.lower() == "zonecommander.lua":
            return decode_any(f.read_bytes()), f.name
    for f in l10n.iterdir():
        if "zonecommander" in f.name.lower() and f.suffix.lower() == ".lua":
            return decode_any(f.read_bytes()), f.name
    return None, None


# ----------------------------- Lua-ish parsing helpers -----------------------------

def extract_balanced_brace_block(text: str, start_idx: int) -> str:
    if start_idx < 0 or start_idx >= len(text) or text[start_idx] != "{":
        raise ValueError("start_idx must point to '{'")
    depth = 0
    end_idx = None
    for i, ch in enumerate(text[start_idx:], start=start_idx):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end_idx = i
                break
    if end_idx is None:
        raise ValueError("Unbalanced braces")
    return text[start_idx:end_idx + 1]

def extract_table_block(text: str, anchor: str) -> str:
    idx = text.find(anchor)
    if idx == -1:
        raise ValueError(f"Anchor not found: {anchor!r}")
    brace_start = text.find("{", idx)
    if brace_start == -1:
        raise ValueError(f"No '{{' found after anchor: {anchor!r}")
    return extract_balanced_brace_block(text, brace_start)

def lua_true_false_to_bool(s: str) -> Optional[bool]:
    if s == "true": return True
    if s == "false": return False
    return None


# ----------------------------- Save parsing -----------------------------

@dataclass
class ZoneState:
    side: Optional[int]
    active: Optional[bool]
    triggers: Dict[str, int]
    remaining_types: Set[str]
    lat: Optional[float]
    lon: Optional[float]

def _parse_remaining_units_types(zone_body: str) -> Set[str]:
    m_ru = re.search(r"\['remainingUnits'\]\s*=\s*{", zone_body)
    if not m_ru:
        return set()
    start = m_ru.end() - 1
    try:
        block = extract_balanced_brace_block(zone_body, start)
    except Exception:
        return set()
    types = set()
    for mt in re.finditer(r"\['([^']+)'\]\s*=\s*(true|false|\d+)", block):
        key = mt.group(1).strip()
        if key and any(c.isalpha() for c in key):
            types.add(key)
    return types

def _parse_latlon(zone_body: str) -> Tuple[Optional[float], Optional[float]]:
    m_ll = re.search(r"\['lat_long'\]\s*=\s*{", zone_body)
    if not m_ll:
        return None, None
    start = m_ll.end() - 1
    try:
        block = extract_balanced_brace_block(zone_body, start)
    except Exception:
        return None, None
    m_lat = re.search(r"\['latitude'\]\s*=\s*([-\d\.]+)", block)
    m_lon = re.search(r"\['longitude'\]\s*=\s*([-\d\.]+)", block)
    lat = float(m_lat.group(1)) if m_lat else None
    lon = float(m_lon.group(1)) if m_lon else None
    return lat, lon

def parse_zones_from_save(save_text: str) -> Dict[str, ZoneState]:
    zones_block = extract_table_block(save_text, "zonePersistance['zones']")
    zones: Dict[str, ZoneState] = {}
    pos = 0
    zone_key_re = re.compile(r"\['([^']+)'\]\s*=\s*{")

    while True:
        m = zone_key_re.search(zones_block, pos)
        if not m:
            break
        name = m.group(1)
        zone_brace_start = m.end() - 1
        zone_body = extract_balanced_brace_block(zones_block, zone_brace_start)

        m_side = re.search(r"\['side'\]\s*=\s*(\d+)", zone_body)
        side = int(m_side.group(1)) if m_side else None

        m_active = re.search(r"\['active'\]\s*=\s*(true|false)", zone_body)
        active = lua_true_false_to_bool(m_active.group(1)) if m_active else None

        triggers: Dict[str, int] = {}
        m_trig = re.search(r"\['triggers'\]\s*=\s*{", zone_body)
        if m_trig:
            trig_start = m_trig.end() - 1
            trig_block = extract_balanced_brace_block(zone_body, trig_start)
            for mt in re.finditer(r"\['([^']+)'\]\s*=\s*(\d+)", trig_block):
                triggers[mt.group(1)] = int(mt.group(2))

        remaining_types = _parse_remaining_units_types(zone_body)
        lat, lon = _parse_latlon(zone_body)

        zones[name] = ZoneState(side, active, triggers, remaining_types, lat, lon)
        pos = zone_brace_start + len(zone_body)

    return zones


# ----------------------------- Extract setup / zoneCommander from miz -----------------------------

def extract_setup_lua_from_miz(miz_path: Path) -> Tuple[str, str]:
    with zipfile.ZipFile(miz_path, "r") as zf:
        members = zf.namelist()
        lua_candidates = [
            m for m in members
            if m.lower().startswith("l10n/default/") and m.lower().endswith(".lua")
        ]
        if not lua_candidates:
            raise FileNotFoundError("No l10n/DEFAULT/*.lua found inside miz")

        def score(name: str) -> Tuple[int, int]:
            ln = name.lower()
            if "ma_setup" in ln:
                s = 3
            elif "setup" in ln:
                s = 2
            else:
                s = 1
            return (-s, len(name))

        lua_candidates.sort(key=score)
        for cand in lua_candidates:
            text = decode_any(zf.read(cand))
            if "bc:addConnection" in text:
                return text, cand
        best = lua_candidates[0]
        return decode_any(zf.read(best)), best

def extract_zonecommander_from_miz(miz_path: Path) -> Tuple[Optional[str], Optional[str]]:
    with zipfile.ZipFile(miz_path, "r") as zf:
        members = zf.namelist()
        cand = None
        for m in members:
            if m.lower().endswith("zonecommander.lua"):
                cand = m
                break
        if not cand:
            for m in members:
                if "zonecommander" in m.lower() and m.lower().endswith(".lua"):
                    cand = m
                    break
        if not cand:
            return None, None
        return decode_any(zf.read(cand)), cand

def parse_rename_map(zonecommander_text: str) -> Dict[str, str]:
    m = re.search(r"\brenameMap\b\s*=\s*{", zonecommander_text)
    if not m:
        return {}
    start = m.end() - 1
    block = extract_balanced_brace_block(zonecommander_text, start)
    mapping: Dict[str, str] = {}
    for mt in re.finditer(r'\["([^"]+)"\]\s*=\s*"([^"]*)"', block):
        mapping[mt.group(1)] = mt.group(2)
    return mapping

def parse_waypoint_list(setup_text: str) -> Dict[str, str]:
    m = re.search(r"\bWaypointList\b\s*=\s*{", setup_text)
    if not m:
        return {}
    start = m.end() - 1
    block = extract_balanced_brace_block(setup_text, start)
    out: Dict[str, str] = {}
    for mt in re.finditer(r"\b([A-Za-z0-9_\-]+)\s*=\s*'([^']*)'", block):
        out[mt.group(1)] = mt.group(2)
    for mt in re.finditer(r'\["([^"]+)"\]\s*=\s*\'([^\']*)\'', block):
        out[mt.group(1)] = mt.group(2)
    return out


# ----------------------------- Initial state from setup Lua -----------------------------

def parse_initial_zones(setup_text: str) -> Dict[str, ZoneState]:
    """Parse ZoneCommander:new() calls to derive initial zone ownership and threats."""
    # First, parse the upgrades table to know what red units each upgrade key contains
    upgrade_red_units: Dict[str, Set[str]] = {}
    # Match upgrade entries like: keyName = { ... red = {'unit1', 'unit2'} ... }
    for m in re.finditer(
        r"(\w+)\s*=\s*\{[^}]*red\s*=\s*\{([^}]*)\}",
        setup_text,
    ):
        key = m.group(1)
        units_raw = m.group(2)
        units = set()
        for u in re.finditer(r"'([^']+)'", units_raw):
            units.add(u.group(1))
        if units:
            upgrade_red_units[key] = units

    # Resolve side variables (e.g., Kola uses sideSE, sideNO instead of literals)
    # Collect "local sideXXX = N" declarations (use the first/default value)
    side_vars: Dict[str, int] = {}
    for m in re.finditer(r"local\s+(side\w+)\s*=\s*(\d+)", setup_text):
        var_name = m.group(1)
        if var_name not in side_vars:  # keep first (default) declaration
            side_vars[var_name] = int(m.group(2))

    zones: Dict[str, ZoneState] = {}
    # Can't use simple [^}]+ because of nested {} like crates={}
    # Allow whitespace between new and ({ since some theaters use tabs
    for m in re.finditer(r"ZoneCommander:new\s*\(\s*\{", setup_text):
        start = m.end() - 1  # points to the opening {
        try:
            body = extract_balanced_brace_block(setup_text, start)
            body = body[1:-1]  # strip outer braces
        except ValueError:
            continue
        m_zone = re.search(r"zone\s*=\s*'([^']+)'", body)
        if not m_zone:
            continue
        zone_name = m_zone.group(1)

        # Try literal side=N first, then variable reference
        m_side = re.search(r"side\s*=\s*(\d+)", body)
        if m_side:
            side = int(m_side.group(1))
        else:
            m_side_var = re.search(r"side\s*=\s*(\w+)", body)
            if m_side_var and m_side_var.group(1) in side_vars:
                side = side_vars[m_side_var.group(1)]
            else:
                continue  # can't determine side

        # Extract threat types from the upgrades reference
        remaining_types: Set[str] = set()
        m_upg = re.search(r"upgrades\s*=\s*upgrades\.(\w+)", body)
        if m_upg:
            upg_key = m_upg.group(1)
            remaining_types = upgrade_red_units.get(upg_key, set()).copy()

        zones[zone_name] = ZoneState(
            side=side, active=True, triggers={},
            remaining_types=remaining_types, lat=None, lon=None,
        )
    return zones


# ----------------------------- Connection parsing -----------------------------

def parse_connections(setup_text: str, known_zones: Set[str]) -> List[Tuple[str, str]]:
    conns: List[Tuple[str, str]] = []
    for m in re.finditer(r'bc:addConnection\("([^"]+)"\s*,\s*"([^"]+)"\)', setup_text):
        a, b = m.group(1), m.group(2)
        if a in known_zones and b in known_zones:
            conns.append((a, b))
    return conns

def build_adjacency(zones: Dict[str, ZoneState], connections: List[Tuple[str, str]]) -> Dict[str, Set[str]]:
    adj: Dict[str, Set[str]] = {z: set() for z in zones.keys()}
    for a, b in connections:
        adj[a].add(b); adj[b].add(a)
    return adj


# ----------------------------- Logic -----------------------------

def is_disabled(z: ZoneState) -> bool:
    return any(k.startswith("disable") and v != 0 for k, v in (z.triggers or {}).items())

def wpt_tag(zone: str, waypoint_map: Dict[str, str]) -> str:
    return waypoint_map.get(zone, "")

def pretty_type(raw: str, mapping: Dict[str, str]) -> str:
    return mapping.get(raw, raw)

def summarize_threats(raw_types: Set[str], mapping: Dict[str, str], max_items: int = 4) -> str:
    if not raw_types:
        return ""
    threatish = []
    other = []
    for t in raw_types:
        pt = pretty_type(t, mapping)
        if any(k.lower() in pt.lower() for k in THREAT_KEYWORDS):
            threatish.append(pt)
        else:
            other.append(pt)

    def uniq(seq):
        seen = set()
        out = []
        for x in seq:
            if x in seen: continue
            seen.add(x); out.append(x)
        return out

    threatish = uniq(sorted(threatish))
    other = uniq(sorted(other))
    chosen = threatish[:max_items]
    if len(chosen) < max_items:
        chosen += other[: (max_items - len(chosen))]
    if not chosen:
        return ""
    suffix = "\u2026" if (len(threatish) + len(other)) > len(chosen) else ""
    return ", ".join(chosen) + suffix

def compute_frontline_for_view(zones, connections, friendly_side, enemy_side):
    ff, ef = set(), set()
    for a, b in connections:
        za, zb = zones.get(a), zones.get(b)
        if not za or not zb: continue
        if not za.active or not zb.active: continue
        if za.side == friendly_side and zb.side == enemy_side:
            ff.add(a); ef.add(b)
        elif za.side == enemy_side and zb.side == friendly_side:
            ef.add(a); ff.add(b)
    return ff, ef

def compute_immediate_attack(zones, enemy_frontline, enemy_side):
    out = []
    for name in sorted(enemy_frontline):
        z = zones[name]
        if z.side != enemy_side or not z.active: continue
        lname = name.lower()
        if "sam" in lname or "defence" in lname: continue
        out.append(name)
    return out

def compute_immediate_infra(zones, enemy_frontline, enemy_side):
    out = []
    for name in sorted(enemy_frontline):
        if name not in INFRA_NAMES: continue
        z = zones[name]
        if z.side == enemy_side and z.active and not is_disabled(z):
            out.append(name)
    return out

def compute_immediate_sead(zones, adj, friendly_zones, immediate_attack, enemy_side):
    attack_set = set(immediate_attack)
    out = set()
    for name, z in zones.items():
        if not is_sam_zone_name(name): continue
        if z.side != enemy_side or not z.active: continue
        if is_disabled(z): continue
        neighbors = adj.get(name, set())
        if neighbors & friendly_zones:
            out.add(name); continue
        if neighbors & attack_set:
            out.add(name); continue
    return sorted(out)

def compute_capture_candidates(zones):
    return sorted([n for n, z in zones.items() if z.side == 0 and z.active and "hidden" not in n.lower()])

def build_view(zones, connections, adj, friendly_side, enemy_side):
    ff, ef = compute_frontline_for_view(zones, connections, friendly_side, enemy_side)
    ia = compute_immediate_attack(zones, ef, enemy_side)
    ii = compute_immediate_infra(zones, ef, enemy_side)
    friendly_zones = {n for n, z in zones.items() if z.side == friendly_side and z.active}
    isead = compute_immediate_sead(zones, adj, friendly_zones, ia, enemy_side)
    cap = compute_capture_candidates(zones)
    support = sorted(list(ff))
    return {
        "friendly_held_count": sum(1 for z in zones.values() if z.active and z.side == friendly_side),
        "enemy_held_count": sum(1 for z in zones.values() if z.active and z.side == enemy_side),
        "neutral_count": sum(1 for z in zones.values() if z.active and z.side == 0),
        "frontline_friendly": sorted(list(ff)),
        "frontline_enemy": sorted(list(ef)),
        "immediate": {
            "attack": ia,
            "infrastructure": ii,
            "sead": isead,
            "support": {"resupply_candidates": support},
            "capture_candidates": cap,
        }
    }

def find_campaign_save(save_dir: Path) -> Optional[Path]:
    if not save_dir.exists() or not save_dir.is_dir():
        return None
    candidates = [p for p in save_dir.iterdir() if p.is_file() and SAVE_NAME_WHITELIST_RE.match(p.name)]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for p in candidates:
        try:
            txt = decode_any(p.read_bytes())
            if "zonePersistance['zones']" in txt:
                return p
        except Exception:
            continue
    return None

def build_snapshot(miz_path: Optional[Path] = None, theater_dir: Optional[Path] = None):
    if theater_dir:
        base_dir = theater_dir
    else:
        base_dir = miz_path.parent

    # Locate Missions/Saves/ by finding the Saved Games root
    sg_root = find_saved_games_root(base_dir)
    if sg_root:
        save_dir = sg_root / "Missions" / "Saves"
    else:
        # Fallback: try relative path (works in some dev layouts)
        save_dir = base_dir / ".." / "Saves"

    status = "ok"
    notes = []

    try:
        if theater_dir:
            setup_text, setup_member = extract_setup_lua_from_dir(theater_dir)
        else:
            setup_text, setup_member = extract_setup_lua_from_miz(miz_path)
    except Exception as e:
        status = "setup_missing"
        setup_text, setup_member = "", ""
        notes.append(f"Failed to extract setup Lua: {e}")

    waypoint_map = parse_waypoint_list(setup_text) if setup_text else {}
    if not waypoint_map:
        notes.append("WaypointList not found; waypoint tags disabled.")

    if theater_dir:
        zc_text, zc_member = extract_zonecommander_from_dir(theater_dir)
    else:
        zc_text, zc_member = extract_zonecommander_from_miz(miz_path)
    pretty_map = parse_rename_map(zc_text) if zc_text else {}
    if not pretty_map:
        notes.append("renameMap not found; pretty threat names disabled.")

    save_path = find_campaign_save(save_dir)
    zones = {}
    connections = []
    adj = {}
    data_source = "none"

    if save_path is not None:
        try:
            save_text = decode_any(save_path.read_bytes())
            zones = parse_zones_from_save(save_text)
            data_source = "save"
        except Exception as e:
            status = "save_unreadable" if status == "ok" else status
            notes.append(f"Failed to parse campaign save: {save_path.name} ({e})")

    # Fallback: derive initial state from setup Lua when no save exists
    if not zones and setup_text:
        try:
            zones = parse_initial_zones(setup_text)
            data_source = "initial"
            if zones:
                notes.append("Using initial zone state from mission setup (no campaign save yet).")
            else:
                status = "setup_parse_error" if status == "ok" else status
                notes.append("Failed to parse initial zones from setup Lua.")
        except Exception as e:
            status = "setup_parse_error" if status == "ok" else status
            notes.append(f"Failed to parse initial zones: {e}")

    if zones and setup_text:
        try:
            connections = parse_connections(setup_text, set(zones.keys()))
            adj = build_adjacency(zones, connections)
        except Exception as e:
            status = "setup_parse_error" if status == "ok" else status
            notes.append(f"Failed to parse connections from setup Lua: {e}")

    if zones and connections and adj:
        views = {
            "blue": build_view(zones, connections, adj, 2, 1),
            "red":  build_view(zones, connections, adj, 1, 2),
        }
    else:
        views = {
            "blue": {"immediate": {"attack": [], "infrastructure": [], "sead": [], "support": {"resupply_candidates": []}, "capture_candidates": []}},
            "red":  {"immediate": {"attack": [], "infrastructure": [], "sead": [], "support": {"resupply_candidates": []}, "capture_candidates": []}},
        }

    zone_types = {zn: zs.remaining_types for zn, zs in zones.items()} if zones else {}
    zone_latlon = {zn: (zs.lat, zs.lon) for zn, zs in zones.items()} if zones else {}

    snapshot = {
        "schema_version": "PWPNG-5.0",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "meta": {
            "status": status,
            "data_source": data_source,  # "save", "initial", or "none"
            "source": str(theater_dir) if theater_dir else str(miz_path),
            "mode": "directory" if theater_dir else "miz",
            "base_dir": str(base_dir),
            "save_dir": str(save_dir),
            "save_file_used": str(save_path) if save_path else None,
            "setup_member_used": setup_member if setup_member else None,
            "zonecommander_member_used": zc_member if zc_member else None,
            "notes": notes,
        },
        "views": views,
    }
    return snapshot, zone_types, pretty_map, waypoint_map, zone_latlon


# ----------------------------- Task line builder (unchanged) -----------------------------

def build_task_lines(immediate, side_label, zone_types, pretty_map, waypoint_map, zone_latlon):
    attack = immediate.get("attack", []) or []
    infra = set(immediate.get("infrastructure", []) or [])
    sead  = immediate.get("sead", []) or []
    support = (immediate.get("support", {}) or {}).get("resupply_candidates", []) or []
    capture = immediate.get("capture_candidates", []) or []

    def ref_line(zone: str) -> str:
        lat, lon = zone_latlon.get(zone, (None, None))
        ll = format_latlon(lat, lon)
        wp = wpt_tag(zone, waypoint_map)
        parts = []
        if wp:
            parts.append(f"WPT{wp.strip()}")
        if ll:
            parts.append(ll)
        return " \u00b7 ".join(parts)

    lines = []
    for z in sead:
        hint = summarize_threats(zone_types.get(z, set()), pretty_map, 4)
        note = "Suppress air defenses impacting the main effort."
        if hint:
            note += f" Primary systems: {hint}."
        ref = ref_line(z)
        if ref:
            note += f" REF: {ref}."
        lines.append(("P1", "SEAD", f"{z}{wpt_tag(z, waypoint_map)}", note))

    for z in attack:
        hint = summarize_threats(zone_types.get(z, set()), pretty_map, 4)
        ref = ref_line(z)
        if z in infra:
            note = "High-value target set. Confirm complete destruction."
            if hint:
                note += f" Expected threats: {hint}."
            if ref:
                note += f" REF: {ref}."
            lines.append(("P2" if sead else "P1", "STRIKE", f"{z}{wpt_tag(z, waypoint_map)}", note))
        else:
            note = "Fix/destroy enemy forces in the objective area."
            if hint:
                note += f" Expected threats: {hint}."
            if ref:
                note += f" REF: {ref}."
            lines.append(("P2" if sead else "P1", "ATTACK", f"{z}{wpt_tag(z, waypoint_map)}", note))

    for z in support:
        note = f"{side_label} forward sustainment hub."
        ref = ref_line(z)
        if ref:
            note += f" REF: {ref}."
        lines.append(("P3", "SUPPORT", f"{z}{wpt_tag(z, waypoint_map)}", note))

    for z in capture:
        note = "Seize and hold once neutralized."
        ref = ref_line(z)
        if ref:
            note += f" REF: {ref}."
        lines.append(("P3", "CAPTURE", f"{z}{wpt_tag(z, waypoint_map)}", note))

    pri_order = {"P1": 1, "P2": 2, "P3": 3}
    lines.sort(key=lambda x: (pri_order.get(x[0], 9), x[1], x[2]))
    return lines


# ----------------------------- Pillow Drawing Helpers -----------------------------

def _wrap_text(text: str, fnt: ImageFont.FreeTypeFont, max_w: int) -> List[str]:
    """Word-wrap text to fit within max_w pixels."""
    words = text.split()
    lines: List[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = fnt.getbbox(test)
        tw = bbox[2] - bbox[0]
        if tw <= max_w or not current:
            current = test
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]

def _text_width(text: str, fnt: ImageFont.FreeTypeFont) -> int:
    bbox = fnt.getbbox(text)
    return bbox[2] - bbox[0]

def _text_height(fnt: ImageFont.FreeTypeFont) -> int:
    bbox = fnt.getbbox("Ayg|")
    return bbox[3] - bbox[1]


# ----------------------------- Military-Style Rendering -----------------------------

# Paper colors — readable under cockpit lighting / NVGs
PAPER_BG     = (245, 240, 230)   # Warm off-white
INK          = (10, 10, 10)      # Near-black
INK_GREY     = (80, 80, 80)     # Secondary text
RULE_COLOR   = (160, 155, 140)  # Horizontal rules
BANNER_BG    = (30, 30, 30)     # Classification banner
BANNER_TEXT  = (245, 240, 230)
SECTION_BG   = (225, 220, 210)  # Section header background
HIGHLIGHT    = (180, 50, 50)    # Red for threats / emphasis


def _draw_banner(draw: ImageDraw.Draw, y: int, text: str, fnt: ImageFont.FreeTypeFont,
                 w: int) -> int:
    """Draw a full-width classification banner. Returns new y."""
    h = _text_height(fnt) + 8
    draw.rectangle((0, y, w, y + h), fill=BANNER_BG)
    tw = _text_width(text, fnt)
    draw.text(((w - tw) // 2, y + 4), text, fill=BANNER_TEXT, font=fnt)
    return y + h


def _draw_rule(draw: ImageDraw.Draw, y: int, x0: int, x1: int) -> int:
    """Draw a horizontal rule. Returns new y."""
    draw.line((x0, y, x1, y), fill=RULE_COLOR)
    return y + 1


def _draw_section_header(draw: ImageDraw.Draw, y: int, text: str,
                         fnt: ImageFont.FreeTypeFont, x0: int, x1: int) -> int:
    """Draw a section header bar. Returns new y."""
    h = _text_height(fnt) + 6
    draw.rectangle((x0, y, x1, y + h), fill=SECTION_BG)
    draw.text((x0 + 6, y + 3), text, fill=INK, font=fnt)
    return y + h + 2


def render_briefing_image(snapshot, side, zone_types, pretty_map, waypoint_map, zone_latlon) -> Image.Image:
    img = Image.new("RGB", (IMG_W, IMG_H), PAPER_BG)
    draw = ImageDraw.Draw(img)

    # Fonts — monospace-heavy for military aesthetic
    f_banner = font("bold", 10)
    f_title  = font("bold", 14)
    f_sub    = font("mono", 9)
    f_sect   = font("bold", 11)
    f_body   = font("mono", 10)
    f_bold   = font("bold", 10)
    f_small  = font("mono", 9)
    f_foot   = font("mono", 8)

    lh = _text_height(f_body) + 3  # standard line height
    lh_sm = _text_height(f_small) + 2
    margin = 20
    content_w = IMG_W - margin * 2

    generated_utc = snapshot.get("generated_utc", "N/A")
    meta = snapshot.get("meta", {}) or {}
    status = meta.get("status", "ok")
    data_source = meta.get("data_source", "none")

    views = snapshot.get("views", {}) or {}
    view = views.get(side, {}) or {}
    immediate = view.get("immediate", {}) or {}
    has_views = bool(view.get("friendly_held_count"))

    coalition = side.upper()

    # ================================================================
    # TOP CLASSIFICATION BANNER
    # ================================================================
    y = _draw_banner(draw, 0, "UNCLASSIFIED // FOUO // FOOTHOLD", f_banner, IMG_W)
    y += 4

    # ================================================================
    # HEADER BLOCK
    # ================================================================
    draw.text((margin, y), "COMBINED JOINT FORCES AIR COMPONENT", fill=INK, font=f_title)
    y += _text_height(f_title) + 2
    draw.text((margin, y), "FRAGMENTARY ORDER / ATO EXTRACT", fill=INK, font=f_bold)
    y += _text_height(f_bold) + 4

    # DTG and meta line
    dtg_line = f"DTG: {fmt_time_block(generated_utc)}    COALITION: {coalition}"
    draw.text((margin, y), dtg_line, fill=INK, font=f_sub)
    y += lh_sm

    # Theater & data source
    source_path = meta.get("source", "")
    theater_name = "UNKNOWN"
    # Try to extract theater name from source path
    for t in ("Caucasus", "Syria", "Kola", "Iraq", "Sinai", "PersianGulf", "Germany"):
        if t.lower() in source_path.lower():
            theater_name = t.upper()
            break

    status_tag = "INITIAL DEPLOYMENT" if data_source == "initial" else (
        "CAMPAIGN IN PROGRESS" if data_source == "save" else "NO DATA"
    )
    draw.text((margin, y), f"THEATER: {theater_name}    STATUS: {status_tag}", fill=INK, font=f_sub)
    y += lh_sm + 2

    y = _draw_rule(draw, y, margin, IMG_W - margin)
    y += 4

    # ================================================================
    # 1. SITUATION
    # ================================================================
    y = _draw_section_header(draw, y, "1. SITUATION", f_sect, margin, IMG_W - margin)

    if has_views:
        held = view.get("friendly_held_count", 0)
        enemy = view.get("enemy_held_count", 0)
        neutral = view.get("neutral_count", 0)

        draw.text((margin + 4, y), "a. Enemy Forces:", fill=INK, font=f_bold)
        y += lh
        enemy_text = f"   RED controls {enemy} zone(s). Defensive posture with integrated"
        draw.text((margin + 4, y), enemy_text, fill=INK, font=f_body)
        y += lh
        draw.text((margin + 4, y), "   air defense network. Expect SAM, AAA, and armor.", fill=INK, font=f_body)
        y += lh + 2

        # List SEAD threats
        sead_zones = immediate.get("sead", []) or []
        if sead_zones:
            draw.text((margin + 4, y), "   IADS THREAT:", fill=HIGHLIGHT, font=f_bold)
            y += lh
            for sz in sead_zones[:4]:
                threats = summarize_threats(zone_types.get(sz, set()), pretty_map, 6)
                wpt = wpt_tag(sz, waypoint_map)
                threat_line = f"   - {sz}{wpt}: {threats}" if threats else f"   - {sz}{wpt}"
                for wl in _wrap_text(threat_line, f_body, content_w - 12):
                    draw.text((margin + 4, y), wl, fill=HIGHLIGHT, font=f_body)
                    y += lh

        y += 2
        draw.text((margin + 4, y), "b. Friendly Forces:", fill=INK, font=f_bold)
        y += lh
        hubs = view.get("frontline_friendly", []) or []
        hub_str = ", ".join(f"{h}{wpt_tag(h, waypoint_map)}" for h in hubs[:5])
        if not hub_str:
            hub_str = "N/A"
        draw.text((margin + 4, y), f"   {coalition} holds {held} zone(s). FWD bases: {hub_str}", fill=INK, font=f_body)
        y += lh
        draw.text((margin + 4, y), f"   Neutral zones: {neutral}. Total AO zones: {held + enemy + neutral}", fill=INK_GREY, font=f_body)
        y += lh + 2
    else:
        draw.text((margin + 4, y), "   No operational data available. Awaiting mission initialization.", fill=INK_GREY, font=f_body)
        y += lh + 2

    y = _draw_rule(draw, y, margin, IMG_W - margin)
    y += 4

    # ================================================================
    # 2. MISSION
    # ================================================================
    y = _draw_section_header(draw, y, "2. MISSION", f_sect, margin, IMG_W - margin)

    objs = immediate.get("attack", []) or []
    sead = immediate.get("sead", []) or []
    capture = immediate.get("capture_candidates", []) or []

    if data_source == "initial" and objs:
        mission_text = (
            f"Coalition forces conduct offensive air operations to neutralize "
            f"enemy defenses and seize {objs[0]}{wpt_tag(objs[0], waypoint_map)} "
            f"in order to establish a forward operating base and enable "
            f"follow-on operations deeper into the AO."
        )
    elif objs:
        mission_text = (
            f"Coalition forces conduct offensive air operations to destroy "
            f"enemy forces at {objs[0]}{wpt_tag(objs[0], waypoint_map)} "
            f"and shape the forward edge for continued advance."
        )
    else:
        mission_text = (
            "Coalition forces maintain defensive posture. Conduct "
            "reconnaissance and prepare for follow-on tasking."
        )

    for ml in _wrap_text(mission_text, f_body, content_w - 8):
        draw.text((margin + 4, y), ml, fill=INK, font=f_body)
        y += lh
    y += 2

    y = _draw_rule(draw, y, margin, IMG_W - margin)
    y += 4

    # ================================================================
    # 3. EXECUTION
    # ================================================================
    y = _draw_section_header(draw, y, "3. EXECUTION", f_sect, margin, IMG_W - margin)

    task_letter = ord('a')

    if sead:
        draw.text((margin + 4, y), f"{chr(task_letter)}. SEAD / DEAD", fill=INK, font=f_bold)
        task_letter += 1
        y += lh
        for sz in sead[:4]:
            threats = summarize_threats(zone_types.get(sz, set()), pretty_map, 5)
            wpt = wpt_tag(sz, waypoint_map)
            ref_lat, ref_lon = zone_latlon.get(sz, (None, None))
            ref_str = format_latlon(ref_lat, ref_lon)
            line1 = f"   TGT: {sz}{wpt}"
            if ref_str:
                line1 += f"  ({ref_str})"
            draw.text((margin + 4, y), line1, fill=INK, font=f_body)
            y += lh
            if threats:
                draw.text((margin + 4, y), f"   SYS: {threats}", fill=HIGHLIGHT, font=f_body)
                y += lh
        draw.text((margin + 4, y), "   TASK: Suppress/destroy prior to main strike package TOT.", fill=INK_GREY, font=f_body)
        y += lh + 2

    if objs:
        infra = set(immediate.get("infrastructure", []) or [])
        draw.text((margin + 4, y), f"{chr(task_letter)}. OCA / STRIKE", fill=INK, font=f_bold)
        task_letter += 1
        y += lh
        for oz in objs[:5]:
            threats = summarize_threats(zone_types.get(oz, set()), pretty_map, 4)
            wpt = wpt_tag(oz, waypoint_map)
            ref_lat, ref_lon = zone_latlon.get(oz, (None, None))
            ref_str = format_latlon(ref_lat, ref_lon)
            is_infra = oz in infra
            label = "STRIKE" if is_infra else "ATTACK"
            line1 = f"   {label}: {oz}{wpt}"
            if ref_str:
                line1 += f"  ({ref_str})"
            draw.text((margin + 4, y), line1, fill=INK, font=f_body)
            y += lh
            if threats:
                draw.text((margin + 4, y), f"   THREATS: {threats}", fill=INK_GREY, font=f_body)
                y += lh
        y += 2

    if capture:
        draw.text((margin + 4, y), f"{chr(task_letter)}. SEIZURE OBJECTIVES", fill=INK, font=f_bold)
        task_letter += 1
        y += lh
        for cz in capture[:4]:
            wpt = wpt_tag(cz, waypoint_map)
            draw.text((margin + 4, y), f"   OBJ: {cz}{wpt} - Seize and hold once neutralized.", fill=INK, font=f_body)
            y += lh
        y += 2

    # Support / sustainment
    support = (immediate.get("support", {}) or {}).get("resupply_candidates", []) or []
    if support:
        draw.text((margin + 4, y), f"{chr(task_letter)}. SUSTAINMENT", fill=INK, font=f_bold)
        task_letter += 1
        y += lh
        sup_str = ", ".join(f"{s}{wpt_tag(s, waypoint_map)}" for s in support[:4])
        draw.text((margin + 4, y), f"   FWD ARMING/REFUEL: {sup_str}", fill=INK, font=f_body)
        y += lh + 2

    if not sead and not objs and not capture:
        draw.text((margin + 4, y), "   No immediate tasking. Maintain CAP/DCA posture.", fill=INK_GREY, font=f_body)
        y += lh + 2

    y = _draw_rule(draw, y, margin, IMG_W - margin)
    y += 4

    # ================================================================
    # 4. COORDINATING INSTRUCTIONS
    # ================================================================
    y = _draw_section_header(draw, y, "4. COORD INSTRUCTIONS", f_sect, margin, IMG_W - margin)

    coord_lines = [
        "a. ROE: As per theater SOP. PID required for all engagements.",
        "b. IFF: Mode 4 ON at all times. Squawk as assigned.",
        "c. RECOVERY: RTB to nearest friendly airfield.",
        "d. CSAR: Report downed aircrew on Guard 243.0 / 121.5.",
        f"e. COMMS: SRS auto-connect enabled. Check in on GCI freq.",
    ]
    for cl in coord_lines:
        for wl in _wrap_text(cl, f_body, content_w - 8):
            draw.text((margin + 4, y), wl, fill=INK, font=f_body)
            y += lh
    y += 2

    y = _draw_rule(draw, y, margin, IMG_W - margin)
    y += 4

    # ================================================================
    # 5. ADMIN / LOGISTICS
    # ================================================================
    if y + 60 < IMG_H - 30:
        y = _draw_section_header(draw, y, "5. ADMIN / LOGISTICS", f_sect, margin, IMG_W - margin)
        admin_lines = [
            "a. Loadout per mission type. Consult server SOP for restrictions.",
            "b. CTLD enabled for logistics and troop transport.",
            "c. Zone capture requires ground presence - deploy troops via CTLD.",
        ]
        for al in admin_lines:
            for wl in _wrap_text(al, f_body, content_w - 8):
                draw.text((margin + 4, y), wl, fill=INK, font=f_body)
                y += lh
        y += 2
        y = _draw_rule(draw, y, margin, IMG_W - margin)

    # ================================================================
    # FOOTER
    # ================================================================
    y = max(y + 4, IMG_H - 30)
    draw.text((margin, y), f"Generated: {generated_utc}  |  Data: {data_source}  |  Foothold Extended", fill=INK_GREY, font=f_foot)
    y += _text_height(f_foot) + 4

    # BOTTOM CLASSIFICATION BANNER
    _draw_banner(draw, IMG_H - _text_height(f_banner) - 8, "UNCLASSIFIED // FOUO // FOOTHOLD", f_banner, IMG_W)

    return img


# ----------------------------- Inject PNG into .miz -----------------------------

def inject_kneeboard_png(miz_path: Path, png_path: Path, inside_name: str) -> None:
    arcname = f"KNEEBOARD/IMAGES/{inside_name}"
    with tempfile.TemporaryDirectory(prefix="miz_patch_") as td:
        tmp_miz = Path(td) / (miz_path.stem + ".__tmp__.miz")
        with zipfile.ZipFile(miz_path, "r") as zin, zipfile.ZipFile(tmp_miz, "w") as zout:
            for item in zin.infolist():
                if item.filename == arcname:
                    continue
                data = zin.read(item.filename)
                zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
                zi.compress_type = item.compress_type
                zi.external_attr = item.external_attr
                zi.comment = item.comment
                zi.extra = item.extra
                zout.writestr(zi, data)
            zout.write(png_path, arcname, compress_type=zipfile.ZIP_DEFLATED)
        bak = miz_path.with_suffix(".miz.bak")
        shutil.copy2(miz_path, bak)
        os.replace(tmp_miz, miz_path)


# ----------------------------- Saved Games root detection -----------------------------

def find_saved_games_root(start: Path) -> Optional[Path]:
    """Walk up from start to find the DCS Saved Games root.

    The root is identified by having a Config/ directory (which contains
    serverSettings.lua, options.lua, etc.).  Works for both client and
    dedicated-server installs regardless of folder depth.

    Production layout example:
        Saved Games/DCS.xxx/Missions/Foothold - Caucasus/briefing.pyw
        Saved Games/DCS.xxx/Config/serverSettings.lua   <-- root marker
        Saved Games/DCS.xxx/KNEEBOARD/                  <-- deploy target
    """
    current = start.resolve()
    # Walk up at most 6 levels (safety limit)
    for _ in range(6):
        if (current / "Config").is_dir():
            return current
        parent = current.parent
        if parent == current:
            break  # filesystem root
        current = parent
    return None


# ----------------------------- Deploy to KNEEBOARD/ -----------------------------

def deploy_kneeboard(blue_img: Image.Image, kneeboard_dir: Path, filename: str = "01_FRAGO.png") -> Path:
    """Write blue briefing PNG to the Saved Games KNEEBOARD/ root directory."""
    kneeboard_dir.mkdir(parents=True, exist_ok=True)
    out_path = kneeboard_dir / filename
    blue_img.save(out_path, "PNG")
    return out_path


# ----------------------------- File watcher (Windows kernel event) -----------------------------

def _watch_directory(path: Path, callback, debounce_sec: float = 10.0):
    """Block and call callback() when .lua files change in path.

    Uses ReadDirectoryChangesW — the thread sleeps in the Windows kernel
    with zero CPU usage until a filesystem write occurs.
    """
    import ctypes
    import ctypes.wintypes

    FILE_LIST_DIRECTORY = 0x01
    OPEN_EXISTING = 3
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    FILE_NOTIFY_CHANGE_FILE_NAME = 0x01
    FILE_NOTIFY_CHANGE_LAST_WRITE = 0x10
    FILE_SHARE_ALL = 0x07
    INVALID_HANDLE = ctypes.wintypes.HANDLE(-1).value

    kernel32 = ctypes.windll.kernel32

    handle = kernel32.CreateFileW(
        str(path), FILE_LIST_DIRECTORY, FILE_SHARE_ALL,
        None, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS, None,
    )
    if handle == INVALID_HANDLE:
        raise OSError(f"Cannot watch directory: {path}")

    buf = ctypes.create_string_buffer(4096)
    bytes_ret = ctypes.wintypes.DWORD()
    last_fire = 0.0

    try:
        while True:
            # Blocks here — zero CPU until a file changes
            ok = kernel32.ReadDirectoryChangesW(
                handle, buf, len(buf), True,
                FILE_NOTIFY_CHANGE_FILE_NAME | FILE_NOTIFY_CHANGE_LAST_WRITE,
                ctypes.byref(bytes_ret), None, None,
            )
            if not ok:
                import time; time.sleep(1)
                continue

            # Parse FILE_NOTIFY_INFORMATION to check if a .lua changed
            offset = 0
            triggered = False
            while True:
                next_off = int.from_bytes(buf[offset:offset + 4], "little")
                name_len = int.from_bytes(buf[offset + 8:offset + 12], "little")
                name = buf[offset + 12:offset + 12 + name_len].decode("utf-16-le", errors="replace")
                if name.lower().endswith(".lua"):
                    triggered = True
                if next_off == 0:
                    break
                offset += next_off

            if triggered:
                import time
                now = time.time()
                if now - last_fire >= debounce_sec:
                    last_fire = now
                    callback()
    finally:
        kernel32.CloseHandle(handle)


def _get_briefing_pids() -> list[int]:
    """Get PIDs of all python/pythonw processes running briefing.pyw."""
    pids = []
    my_pid = os.getpid()
    try:
        import subprocess
        # Use PowerShell Get-CimInstance (works on Windows 10/11, wmic is deprecated)
        ps_cmd = (
            "Get-CimInstance Win32_Process "
            "| Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*briefing.pyw*' } "
            "| Select-Object -ExpandProperty ProcessId"
        )
        CREATE_NO_WINDOW = 0x08000000
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            text=True, stderr=subprocess.DEVNULL, timeout=10,
            creationflags=CREATE_NO_WINDOW,
        )
        for line in out.strip().splitlines():
            line = line.strip()
            if line.isdigit():
                pid = int(line)
                if pid != my_pid:
                    pids.append(pid)
    except Exception:
        pass
    return pids


def _is_already_running() -> bool:
    """Check if another briefing.pyw process is already running."""
    return len(_get_briefing_pids()) > 0


def _kill_running_watchers() -> int:
    """Kill all running briefing.pyw watcher processes. Returns count killed."""
    pids = _get_briefing_pids()
    killed = 0
    for pid in pids:
        try:
            os.kill(pid, 9)
            killed += 1
        except (ProcessLookupError, PermissionError, OSError):
            pass
    return killed


def _resolve_kneeboard_dir(override: Optional[str], start_path: Path) -> Path:
    """Resolve the KNEEBOARD directory for --deploy.

    Priority:
    1. Explicit --kneeboard-dir override
    2. Auto-detect by walking up from start_path to find the Saved Games root
    3. Fail with a helpful error
    """
    if override:
        return Path(override)
    root = find_saved_games_root(start_path)
    if root:
        return root / "KNEEBOARD"
    raise SystemExit(
        "ERROR: Could not locate the DCS Saved Games root.\n"
        "Expected to find a Config/ directory above the mission folder.\n"
        "Use --kneeboard-dir to specify the KNEEBOARD path manually.\n\n"
        f"Searched upward from: {start_path}"
    )


# ----------------------------- Main -----------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate Foothold coalition briefing kneeboard.",
        epilog=(
            "Examples:\n"
            "  python briefing.pyw Caucasus                Generate blue briefing from unpacked dir\n"
            "  python briefing.pyw Caucasus --deploy        Generate + deploy to KNEEBOARD/\n"
            "  python briefing.pyw Foothold.miz             Generate from .miz file\n"
            "  python briefing.pyw Caucasus --red            Also generate red (debug only)\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("target", nargs="?", default=None,
                    help="A .miz file or an unpacked theater directory. "
                         "Omit to auto-detect a .miz in the current dir.")
    ap.add_argument("--deploy", action="store_true",
                    help="Deploy blue briefing to Saved Games KNEEBOARD/ root")
    ap.add_argument("--kneeboard-dir", type=str, default=None,
                    help="Override KNEEBOARD directory path for --deploy")
    ap.add_argument("--red", action="store_true",
                    help="Also generate red briefing (debug only, not deployed)")
    ap.add_argument("--no-watch", action="store_true",
                    help="Generate once and exit (don't monitor for save changes)")
    ap.add_argument("--stop", action="store_true",
                    help="Kill all running briefing.pyw watchers and exit")
    ap.add_argument("--kneeboard-name", type=str, default="BRIEF_BLUE.png",
                    help="Filename for the injected kneeboard PNG (miz mode only)")
    args = ap.parse_args()

    # --stop: kill all running watchers and exit
    if args.stop:
        killed = _kill_running_watchers()
        if killed:
            print(f"Stopped {killed} running briefing watcher(s).")
        else:
            print("No running briefing watchers found.")
        return

    target = Path(args.target).resolve() if args.target else None

    # --- Directory mode: target exists and is not a .miz ---
    if target and target.suffix.lower() != ".miz":
        if not target.is_dir():
            raise SystemExit(f"ERROR: Not a file or directory: {target}")
        l10n = target / "l10n" / "DEFAULT"
        if not l10n.is_dir():
            raise SystemExit(
                f"ERROR: {target.name} doesn't look like an unpacked Foothold theater.\n"
                f"Expected l10n/DEFAULT/ with Lua scripts inside."
            )

        print(f"Directory mode: {target.name}")
        snapshot, zone_types, pretty_map, waypoint_map, zone_latlon = build_snapshot(theater_dir=target)

        blue_png = target / "briefing_blue.png"
        blue_img = render_briefing_image(snapshot, "blue", zone_types, pretty_map, waypoint_map, zone_latlon)
        blue_img.save(blue_png, "PNG")
        print(f"Wrote: {blue_png}")

        if args.red:
            red_png = target / "briefing_red.png"
            red_img = render_briefing_image(snapshot, "red", zone_types, pretty_map, waypoint_map, zone_latlon)
            red_img.save(red_png, "PNG")
            print(f"Wrote: {red_png} (debug)")

        if args.deploy:
            kb_dir = _resolve_kneeboard_dir(args.kneeboard_dir, target)
            deployed = deploy_kneeboard(blue_img, kb_dir)
            print(f"Deployed: {deployed}")

        print(f"Status: {snapshot.get('meta', {}).get('status', 'unknown')}")
        return

    # --- Miz mode: explicit .miz or auto-detect ---
    # Production mode: extract data from .miz, deploy kneeboard to KNEEBOARD/.
    # No injection into the .miz, no local PNG files written.
    if target:
        if not target.is_file():
            raise SystemExit(f"ERROR: File not found: {target}")
        miz_path = target
        print(f"Using: {miz_path.name}")
    else:
        miz_path = find_single_miz(Path.cwd())

    kb_dir = _resolve_kneeboard_dir(args.kneeboard_dir, miz_path.parent)

    def generate():
        snapshot, zone_types, pretty_map, waypoint_map, zone_latlon = build_snapshot(miz_path=miz_path)
        blue_img = render_briefing_image(snapshot, "blue", zone_types, pretty_map, waypoint_map, zone_latlon)
        deployed = deploy_kneeboard(blue_img, kb_dir)
        status = snapshot.get('meta', {}).get('status', 'unknown')
        data_src = snapshot.get('meta', {}).get('data_source', 'none')
        print(f"Deployed: {deployed}  [status={status}, source={data_src}]")

    # Initial generation
    generate()

    if args.red:
        snapshot, zone_types, pretty_map, waypoint_map, zone_latlon = build_snapshot(miz_path=miz_path)
        out_dir = miz_path.parent
        red_png = out_dir / "briefing_red.png"
        red_img = render_briefing_image(snapshot, "red", zone_types, pretty_map, waypoint_map, zone_latlon)
        red_img.save(red_png, "PNG")
        print(f"Wrote: {red_png} (debug)")

    # Watch for save file changes and regenerate automatically
    if args.no_watch:
        return

    sg_root = find_saved_games_root(miz_path.parent)
    if not sg_root:
        print("Cannot locate Saved Games root -- skipping watch mode.")
        return

    saves_dir = sg_root / "Missions" / "Saves"
    saves_dir.mkdir(parents=True, exist_ok=True)

    # Check if another briefing.pyw is already watching
    if _is_already_running():
        print("Briefing watcher already running. Exiting.")
        return

    print(f"\nMonitoring {saves_dir} for campaign updates...")
    print("Kneeboard will regenerate automatically when zones change.")
    print("Close this window to stop.\n")

    try:
        _watch_directory(saves_dir, generate)
    except KeyboardInterrupt:
        print("\nStopped.")
    except OSError as e:
        print(f"Watch error: {e} -- exiting.")


if __name__ == "__main__":
    main()
