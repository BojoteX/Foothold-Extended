# Foothold Extended — Sinai Extended

## Overview

Sinai Extended theater for Foothold Extended. DCS map ID: `SinaiMap`.

- **Setup script:** `MA_Setup_Sinai_extended.lua`
- **Era:** Modern / Coldwar (configurable)
- **DTC:** Not included

## Map-Specific Files

- `MA_Setup_Sinai_extended.lua` — zone definitions, upgrade compositions, SAM placements
- `foothold.jpg` — briefing image
- `Channel_kneeboard-AJS37-clean.png` — Viggen-specific kneeboard
- `Lineup_Mission_Kneeboard.png`, `Lineup_Training_Kneeboard.png` — lineup kneeboards

## Script Variants

- **Zeus.lua:** Adds `"CTLD_CARGO_AmmoTruck"` and `"CTLD_CARGO_GMLRS_HE"` to protected unit list
- **Moose_.lua:** Has `if name then` nil-guard patch in CTLD crate loading
- **Splash_Damage_3.4_leka.lua:** Older v3.4 version (other theaters use v3.4.1) — missing duplicate killfeed detection logic

## Notes

- Shares `SinaiMap` theatre ID with Sinai North — these are two different mission layouts on the same DCS map

## Known Issues

- **Older Splash Damage version** — this is the only theater running the actual v3.4 codebase. Consider updating to v3.4.1 for consistency
