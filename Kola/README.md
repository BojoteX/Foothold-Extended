# Foothold Extended — Kola

## Overview

Kola theater for Foothold Extended. DCS map ID: `Kola`.

- **Setup script:** `kola_setup.lua`
- **Era:** Modern / Coldwar (configurable)
- **DTC:** Not included

## Map-Specific Files

- `kola_setup.lua` — zone definitions, upgrade compositions, SAM placements
- `Kola.jpg` — briefing image
- `radio_effect.ogg` — unique audio file not present in other theaters
- Extra kneeboards: `FlightsKneeboard_THT.png`, `fl_checklist_mags.png`, Kallax departure/STAR charts

## Script Variants

- **Zeus.lua:** Adds `"CTLD_CARGO_AmmoTruck"` and `"CTLD_CARGO_GMLRS_HE"` to protected unit list
- **Moose_.lua:** Has BOTH the `if name then` nil-guard patch AND a unique `NotifyGroup` parameter patch in `CTLD:_BuildCrates` — this is the only theater with this modification
- Missing `troops_load_ao.ogg` audio file vs Caucasus

## Notes

- The MOOSE `NotifyGroup` patch routes engineering-mode build crate messages to the correct group — may be a fix for a Kola-specific multiplayer issue
- Foothold Config comments note: era toggle "does not work in Afghanistan or kola" — verify Cold War era behavior

## Known Issues

_None documented yet._
