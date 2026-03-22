# Foothold Extended — Syria

## Overview

Syria theater for Foothold Extended. DCS map ID: `Syria`.

- **Setup script:** `footholdSyriaSetupv3.lua` (6,862 lines)
- **Era:** Modern / Coldwar (configurable)
- **DTC:** Not included

## Map-Specific Files

- `footholdSyriaSetupv3.lua` — zone definitions, upgrade compositions, SAM placements
- `KNEEBOARD/AJS37/IMAGES/` — Viggen-specific kneeboard (unique to Syria)
- `image.jpg` — briefing image

## Script Variants

- **Zeus.lua:** Adds `"CTLD_CARGO_AmmoTruck"` and `"CTLD_CARGO_GMLRS_HE"` to the protected unit list (line 19)
- **Moose_.lua:** Base version (no nil-guard patch, no NotifyGroup patch)
- 20 fewer AIEN combat voice `.ogg` files vs Caucasus (missing infantry chatter audio)

## Notes

_None yet._

## Known Issues

_None documented yet._
