#!/usr/bin/env python3
"""CI tests for briefing.pyw — validates all theaters produce valid FRAG-O data.

No Pillow required. Tests only the data pipeline (parsing, zone resolution,
frontline computation), NOT image rendering.

Run: python -m pytest tests/ -v
  or: python tests/test_briefing.py
"""
from __future__ import annotations

import importlib
import importlib.machinery
import sys
import types
from pathlib import Path

# Add repo root to path so we can import briefing
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# briefing.pyw uses .pyw extension — register it as importable
if ".pyw" not in importlib.machinery.SOURCE_SUFFIXES:
    importlib.machinery.SOURCE_SUFFIXES.append(".pyw")

# Create a stub PIL module so briefing.pyw loads without Pillow.
# We only test the data pipeline, never render images.
_pil = types.ModuleType("PIL")

_img_mod = types.ModuleType("PIL.Image")
_draw_mod = types.ModuleType("PIL.ImageDraw")
_font_mod = types.ModuleType("PIL.ImageFont")

# Minimal stubs so module-level init code doesn't crash
_font_mod.truetype = lambda *a, **kw: None
_font_mod.load_default = lambda *a, **kw: None

class _FakeFont:
    pass

_font_mod.FreeTypeFont = _FakeFont

_pil.Image = _img_mod
_pil.ImageDraw = _draw_mod
_pil.ImageFont = _font_mod
sys.modules["PIL"] = _pil
sys.modules["PIL.Image"] = _img_mod
sys.modules["PIL.ImageDraw"] = _draw_mod
sys.modules["PIL.ImageFont"] = _font_mod

# Now import the functions we need
from briefing import (  # noqa: E402
    build_snapshot,
    parse_initial_zones,
    parse_connections,
    build_adjacency,
    find_saved_games_root,
)

# All theaters in the repo
THEATERS = [
    "Caucasus",
    "Syria",
    "Germany",
    "Iraq",
    "Kola",
    "Persian Gulf",
    "Sinai Extended",
    "Sinai North",
]


def get_theater_dirs():
    """Return list of (name, path) for theaters that exist on disk."""
    dirs = []
    for name in THEATERS:
        p = REPO / name
        if p.is_dir() and (p / "l10n" / "DEFAULT").is_dir():
            dirs.append((name, p))
    return dirs


THEATER_DIRS = get_theater_dirs()


class TestTheaterParsing:
    """Every theater must parse zones, connections, and produce a valid snapshot."""

    def _snapshot(self, theater_dir):
        return build_snapshot(theater_dir=theater_dir)

    def test_all_theaters_present(self):
        found = {name for name, _ in THEATER_DIRS}
        missing = set(THEATERS) - found
        assert not missing, f"Missing theater directories: {missing}"

    def test_zones_parsed(self):
        """Every theater must parse at least 10 zones."""
        for name, path in THEATER_DIRS:
            snap, zone_types, _, _, _ = self._snapshot(path)
            total = len(zone_types)
            assert total >= 10, f"{name}: only {total} zones parsed (expected >= 10)"

    def test_status_ok(self):
        """Every theater must return status 'ok' from initial state."""
        for name, path in THEATER_DIRS:
            snap, _, _, _, _ = self._snapshot(path)
            status = snap["meta"]["status"]
            assert status == "ok", f"{name}: status is '{status}', expected 'ok'"

    def test_data_source_initial(self):
        """Without saves, data_source must be 'initial'."""
        for name, path in THEATER_DIRS:
            snap, _, _, _, _ = self._snapshot(path)
            ds = snap["meta"]["data_source"]
            assert ds == "initial", f"{name}: data_source is '{ds}', expected 'initial'"

    def test_blue_has_zones(self):
        """Blue must hold at least 1 zone in every theater."""
        for name, path in THEATER_DIRS:
            snap, _, _, _, _ = self._snapshot(path)
            blue = snap["views"]["blue"]
            held = blue.get("friendly_held_count", 0)
            assert held >= 1, f"{name}: blue holds {held} zones (expected >= 1)"

    def test_red_has_zones(self):
        """Red must hold zones in every theater (it's PvE, red owns most of the map)."""
        for name, path in THEATER_DIRS:
            snap, _, _, _, _ = self._snapshot(path)
            blue = snap["views"]["blue"]
            enemy = blue.get("enemy_held_count", 0)
            assert enemy >= 5, f"{name}: red holds {enemy} zones (expected >= 5)"

    def test_red_outnumbers_blue(self):
        """In initial state, red must hold more zones than blue."""
        for name, path in THEATER_DIRS:
            snap, _, _, _, _ = self._snapshot(path)
            blue_view = snap["views"]["blue"]
            held = blue_view.get("friendly_held_count", 0)
            enemy = blue_view.get("enemy_held_count", 0)
            assert enemy > held, (
                f"{name}: red ({enemy}) should outnumber blue ({held}) at start"
            )

    def test_has_connections(self):
        """Every theater must have zone connections (the graph that defines the campaign flow)."""
        for name, path in THEATER_DIRS:
            snap, zone_types, _, _, _ = self._snapshot(path)
            # Connections exist if there's a frontline (friendly or enemy frontline zones)
            blue = snap["views"]["blue"]
            ff = blue.get("frontline_friendly", [])
            ef = blue.get("frontline_enemy", [])
            has_front = len(ff) > 0 or len(ef) > 0
            # Or attack targets exist
            atk = blue.get("immediate", {}).get("attack", [])
            assert has_front or len(atk) > 0, (
                f"{name}: no frontline or attack targets — connections may be broken"
            )

    def test_blue_has_attack_targets_or_frontline(self):
        """Blue must have either attack targets or a frontline to advance."""
        for name, path in THEATER_DIRS:
            snap, _, _, _, _ = self._snapshot(path)
            blue = snap["views"]["blue"]
            atk = blue.get("immediate", {}).get("attack", [])
            ff = blue.get("frontline_friendly", [])
            assert len(atk) > 0 or len(ff) > 0, (
                f"{name}: blue has no attack targets and no frontline"
            )

    def test_snapshot_has_required_keys(self):
        """Snapshot structure must have all expected keys."""
        for name, path in THEATER_DIRS:
            snap, _, _, _, _ = self._snapshot(path)
            assert "schema_version" in snap
            assert "generated_utc" in snap
            assert "meta" in snap
            assert "views" in snap
            assert "blue" in snap["views"]
            assert "red" in snap["views"]
            meta = snap["meta"]
            assert "status" in meta
            assert "data_source" in meta

    def test_views_symmetric(self):
        """Both blue and red views must exist and have zone counts."""
        for name, path in THEATER_DIRS:
            snap, _, _, _, _ = self._snapshot(path)
            for side in ("blue", "red"):
                view = snap["views"][side]
                assert "friendly_held_count" in view, f"{name}/{side}: missing friendly_held_count"
                assert "enemy_held_count" in view, f"{name}/{side}: missing enemy_held_count"
                assert "immediate" in view, f"{name}/{side}: missing immediate"


class TestSavedGamesRoot:
    """find_saved_games_root must work from various depths.

    These tests only run on a real DCS install (where Config/ exists).
    Skipped in CI.
    """

    def test_from_theater_dir(self):
        for name, path in THEATER_DIRS:
            root = find_saved_games_root(path)
            if root is None:
                return  # skip — no DCS Saved Games root (CI environment)
            assert (root / "Config").is_dir(), f"Root {root} has no Config/"

    def test_from_repo_root(self):
        root = find_saved_games_root(REPO)
        if root is None:
            return  # skip — no DCS Saved Games root (CI environment)
        assert (root / "Config").is_dir()


# Allow running directly: python tests/test_briefing.py
if __name__ == "__main__":
    import unittest

    # Convert to unittest for standalone execution
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(
        type("TestTheaterParsing", (TestTheaterParsing, unittest.TestCase), {})
    ))
    suite.addTests(loader.loadTestsFromTestCase(
        type("TestSavedGamesRoot", (TestSavedGamesRoot, unittest.TestCase), {})
    ))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
