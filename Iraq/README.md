# Foothold Extended — Iraq (Gulf War)

## Overview

Iraq theater for Foothold Extended. DCS map ID: `Iraq`.

- **Setup script:** `IRAQ_SETUP.lua`
- **Era:** Gulf War
- **DTC:** Not included

## Map-Specific Files

- `IRAQ_SETUP.lua` — zone definitions, upgrade compositions, SAM placements
- `1130px-USAF_F-16A_F-15C_F-15E_Desert_Storm_edit2.jpg` — Desert Storm briefing image
- `Lineup_Mission_Kneeboard.png` — mission lineup kneeboard

## Script Variants

- **Zeus.lua:** Base version (no extra protected units)
- **Moose_.lua:** Has `if name then` nil-guard patch in CTLD crate loading
- Missing `beaconsilent.ogg` and `BH.ogg` audio files vs Caucasus

## Notes

- Gulf War era — config `Era` value should be `"Gulfwar"` (per Foothold Config comments: "Gulfwar" if the map is Iraq)

## Known Issues

_None documented yet._
