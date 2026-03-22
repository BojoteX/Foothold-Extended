# Foothold Extended — Sinai North

## Overview

Sinai North theater for Foothold Extended. DCS map ID: `SinaiMap`.

- **Setup script:** `MA_Setup_north only.lua`
- **Era:** Modern / Coldwar (configurable)
- **DTC:** Not included

## Map-Specific Files

- `MA_Setup_north only.lua` — zone definitions, upgrade compositions, SAM placements (shorter zone layout than Sinai Extended)
- `foothold.jpg` — briefing image
- `Channel_kneeboard-AJS37-clean.png` — Viggen-specific kneeboard
- `Lineup_Mission_Kneeboard.png`, `Lineup_Training_Kneeboard.png` — lineup kneeboards

## Script Variants

- **Zeus.lua:** Adds `"CTLD_CARGO_AmmoTruck"` and `"CTLD_CARGO_GMLRS_HE"` to protected unit list
- **Moose_.lua:** Base version (no nil-guard patch, no NotifyGroup patch — same as Caucasus/Syria)
- **Splash_Damage_3.4_leka.lua:** Filename says v3.4 but content is actually v3.4.1 (byte-identical to other theaters' v3.4.1)

## Notes

- Shares `SinaiMap` theatre ID with Sinai Extended — this is a shorter/focused zone layout on the same DCS map

## Known Issues

- **Splash Damage filename mismatch** — file is named `Splash_Damage_3.4_leka.lua` but contains v3.4.1 code. Cosmetic issue only, no functional impact
