#!/usr/bin/env python3
"""Repack unpacked theater directories into .miz files.

Usage:
    python scripts/repack.py                  # repack all theaters
    python scripts/repack.py Caucasus Syria   # repack specific theaters
    python scripts/repack.py --outdir dist/   # output to dist/

A .miz is a ZIP archive containing the mission files (mission, options,
theatre, warehouses, l10n/, KNEEBOARD/, DTC/) — everything except dev
artifacts like README.md and briefing_*.png.
"""
from __future__ import annotations

import argparse
import os
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Files/dirs to EXCLUDE from the .miz (dev-only artifacts)
EXCLUDE_NAMES = {
    "README.md",
    "CLAUDE.md",
    ".git",
    ".gitignore",
    ".github",
}
EXCLUDE_PREFIXES = ("briefing_",)

# Required files inside a valid theater directory
REQUIRED_FILES = {"mission", "theatre"}

# Theater name -> miz filename mapping
THEATER_MIZ_NAMES = {
    "Caucasus":       "Foothold_Extended_Caucasus",
    "Syria":          "Foothold_Extended_Syria",
    "Germany":        "Foothold_Extended_Germany",
    "Iraq":           "Foothold_Extended_Iraq",
    "Kola":           "Foothold_Extended_Kola",
    "Persian Gulf":   "Foothold_Extended_PersianGulf",
    "Sinai Extended": "Foothold_Extended_SinaiExtended",
    "Sinai North":    "Foothold_Extended_SinaiNorth",
}


def find_theaters(names: list[str] | None = None) -> list[tuple[str, Path]]:
    """Find theater directories in the repo."""
    theaters = []
    for name, _ in THEATER_MIZ_NAMES.items():
        p = REPO / name
        if p.is_dir() and all((p / f).exists() for f in REQUIRED_FILES):
            if names is None or name in names:
                theaters.append((name, p))
    if names:
        found = {n for n, _ in theaters}
        missing = set(names) - found
        if missing:
            print(f"WARNING: theaters not found: {missing}", file=sys.stderr)
    return theaters


def should_include(rel_path: str) -> bool:
    """Check if a file should be included in the .miz."""
    parts = rel_path.replace("\\", "/").split("/")
    for part in parts:
        if part in EXCLUDE_NAMES:
            return False
        if any(part.startswith(pfx) for pfx in EXCLUDE_PREFIXES):
            return False
    return True


def repack_theater(name: str, theater_dir: Path, outdir: Path, version: str | None = None) -> Path:
    """Repack a single theater directory into a .miz file."""
    base_name = THEATER_MIZ_NAMES.get(name, f"Foothold_Extended_{name}")
    if version:
        miz_name = f"{base_name}_{version}.miz"
    else:
        miz_name = f"{base_name}.miz"

    miz_path = outdir / miz_name
    outdir.mkdir(parents=True, exist_ok=True)

    file_count = 0
    with zipfile.ZipFile(miz_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(theater_dir):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_NAMES]
            for f in sorted(files):
                full = Path(root) / f
                rel = full.relative_to(theater_dir).as_posix()
                if should_include(rel):
                    zf.write(full, rel)
                    file_count += 1

    size_mb = miz_path.stat().st_size / (1024 * 1024)
    print(f"  {miz_name} ({file_count} files, {size_mb:.1f} MB)")
    return miz_path


def main():
    ap = argparse.ArgumentParser(description="Repack Foothold theaters into .miz files")
    ap.add_argument("theaters", nargs="*", default=None,
                    help="Theater names to repack (default: all)")
    ap.add_argument("--outdir", type=str, default="dist",
                    help="Output directory (default: dist/)")
    ap.add_argument("--version", type=str, default=None,
                    help="Version tag to append to filenames (e.g. v1.0.0)")
    args = ap.parse_args()

    theaters = find_theaters(args.theaters or None)
    if not theaters:
        print("No theaters found to repack.", file=sys.stderr)
        sys.exit(1)

    outdir = (REPO / args.outdir).resolve()
    print(f"Repacking {len(theaters)} theater(s) to {outdir}/")

    miz_files = []
    for name, path in theaters:
        miz = repack_theater(name, path, outdir, args.version)
        miz_files.append(miz)

    print(f"\nDone. {len(miz_files)} .miz file(s) created.")
    return miz_files


if __name__ == "__main__":
    main()
