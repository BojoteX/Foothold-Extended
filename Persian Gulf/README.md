# Foothold Extended — Persian Gulf

## Overview

Persian Gulf theater for Foothold Extended. DCS map ID: `PersianGulf`.

- **Setup script:** `foothold pg nya.lua`
- **Era:** Modern / Coldwar (configurable)
- **DTC:** 2 files (`SOBY16__2.9.19.13478.dtc`, `SOBY18_2.9.19.13478.dtc`)

## Map-Specific Files

- `foothold pg nya.lua` — zone definitions, upgrade compositions, SAM placements
- `Foothold PG-3.png` — additional kneeboard/map image
- `foothold.jpg` — briefing image
- `Lineup_Training_Kneeboard.png` — training lineup kneeboard

## Script Variants

- **Zeus.lua:** Most extensive protected list — adds `"CTLD_CARGO_HMMWV"`, `"CTLD_CARGO_AmmoTruck"`, and `"CTLD_CARGO_GMLRS_HE"`
- **Moose_.lua:** Has `if name then` nil-guard patch in CTLD crate loading

## Notes

_None yet._

## Known Issues

- **Missing `warehouses` file** — this theater has no `warehouses` file. May need to be regenerated from the DCS editor or sourced from an original .miz
