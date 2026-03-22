# Foothold Extended — Germany (Cold War)

## Overview

Germany Cold War theater for Foothold Extended. DCS map ID: `GermanyCW`.

- **Setup script:** `COLDWAR_SETUP.lua`
- **Era:** Cold War only
- **DTC:** 2 files (`SOBY16__2.9.19.13478.dtc`, `SOBY18_2.9.19.13478.dtc`)

## Map-Specific Files

- `COLDWAR_SETUP.lua` — zone definitions, upgrade compositions, SAM placements
- `Foothold ColdWar 2.jpg` — Cold War briefing image
- `image.png` — kneeboard map image

## Script Variants

- **Zeus.lua:** Base version (no extra protected units)
- **Moose_.lua:** Has `if name then` nil-guard patch in CTLD crate loading

## Notes

- This is a Cold War-only theater — the era toggle in `Foothold Config.lua` should remain set to `"Coldwar"`

## Known Issues

_None documented yet._
