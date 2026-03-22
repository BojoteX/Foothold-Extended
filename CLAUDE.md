# Foothold Extended — Project Context

## What This Is

This repo contains decompressed DCS World mission files (`.miz`) for **Foothold Extended**, a popular multiplayer sandbox mission by **lekaa** (Discord: leka86). A `.miz` is just a ZIP archive — each theater directory here is an unpacked `.miz` ready to be repacked.

The goal is to maintain all 8 theaters in a monorepo with CI-driven `.miz` releases, automated kneeboard generation, and cross-theater consistency tracking.

## Repo Owner

**Bojote** (GitHub/Discord) — also the developer of CockpitOS (DCS custom panels firmware). Collaborating directly with lekaa (the Foothold mission author) to help him adopt GitHub workflows and automate his release process. See Discord DM history with Leka for context on this collaboration.

## Directory Structure

```
Foothold Extended/
├── CLAUDE.md              ← You are here
├── README.md              ← Generic repo overview (all theaters)
├── briefing.pyw           ← Kneeboard briefing generator (Pillow-based)
├── Docs/
│   └── Foothold manual v1.6.pdf   ← Official manual (theater-agnostic)
├── Caucasus/              ← Reference theater (fully researched)
│   ├── README.md          ← Full v2 research document (~994 lines)
│   ├── mission, options, warehouses, theatre
│   └── l10n/DEFAULT/      ← Lua scripts, audio, images
├── Syria/                 ├── README.md + unpacked .miz contents
├── Germany/               ├── Cold War only theater
├── Iraq/                  ├── Gulf War era theater
├── Kola/                  ├── Has unique MOOSE patch
├── Persian Gulf/          ├── Missing warehouses file (known issue)
├── Sinai Extended/        ├── Older Splash Damage v3.4
└── Sinai North/           └── Shorter zone layout on same SinaiMap
```

Each theater directory IS the .miz contents. To repack: `cd Theater && zip -r ../Name.miz . -x "README.md" "briefing_*.png"`.

## Theater Details

| Theater | DCS Map ID | Setup Script | Era | Known Issues |
|---------|-----------|--------------|-----|--------------|
| Caucasus | `Caucasus` | `MA_Setup_CA.lua` | Modern/Coldwar | None — fully researched |
| Syria | `Syria` | `footholdSyriaSetupv3.lua` | Modern/Coldwar | Missing some AIEN voice .ogg files |
| Germany | `GermanyCW` | `COLDWAR_SETUP.lua` | Coldwar only | — |
| Iraq | `Iraq` | `IRAQ_SETUP.lua` | Gulf War | Missing beaconsilent.ogg, BH.ogg |
| Kola | `Kola` | `kola_setup.lua` | Modern/Coldwar | Unique MOOSE patch; era toggle may not work |
| Persian Gulf | `PersianGulf` | `foothold pg nya.lua` | Modern/Coldwar | **Missing `warehouses` file** |
| Sinai Extended | `SinaiMap` | `MA_Setup_Sinai_extended.lua` | Modern/Coldwar | **Older Splash Damage v3.4** |
| Sinai North | `SinaiMap` | `MA_Setup_north only.lua` | Modern/Coldwar | Splash Damage filename says v3.4 but content is v3.4.1 |

## Cross-Theater Script Analysis (completed)

### Byte-identical across all 8 theaters
`zoneCommander.lua`, `Foothold Config.lua`, `Foothold CTLD.lua`, `AIEN.lua`, `EWRS.lua`, `WelcomeMessage.lua`

### Moose_.lua — 3 variants
- **Group A** (Caucasus, Syria, Sinai North): Base version
- **Group B** (Germany, Iraq, PG, Sinai Extended): +nil-guard in CTLD crate loading (`if name then`)
- **Group C** (Kola only): +nil-guard AND unique `NotifyGroup` patch in `CTLD:_BuildCrates`

### Zeus.lua — 3 variants
- **Group A** (Caucasus, Germany, Iraq): Base protected unit list
- **Group B** (Syria, Kola, Sinai Extended, Sinai North): +`CTLD_CARGO_AmmoTruck`, +`CTLD_CARGO_GMLRS_HE`
- **Group C** (Persian Gulf only): +`CTLD_CARGO_HMMWV`, +AmmoTruck, +GMLRS_HE

### Splash_Damage — 2 versions
- **v3.4.1**: Caucasus, Syria, Germany, Iraq, Kola, PG, Sinai North (Sinai North filename says 3.4 but content is 3.4.1)
- **v3.4 (actual old code)**: Sinai Extended only — missing duplicate killfeed detection

### Decision: Keep shared files duplicated per theater
Upstream (lekaa) ships them in each .miz. We never edit these scripts ourselves. CI repacks each theater independently. Deduplicating would add complexity for zero benefit.

## Key Bugs/Issues Found (reported to Leka)

These were identified during cross-theater analysis and communicated to lekaa via Discord DM on 2026-03-21:

1. **Persian Gulf missing `warehouses`** — no airfield inventories, needs regeneration
2. **Sinai Extended on old Splash Damage v3.4** — only theater with actual old code
3. **Moose patches inconsistent** — nil-guard fix in some maps but not others (looks like a real bugfix that should be everywhere)
4. **Zeus protected unit lists diverged** — PG has the most complete list
5. **Missing audio files** — Iraq missing beaconsilent.ogg/BH.ogg, Syria missing ~20 AIEN voice files

## briefing.pyw — Kneeboard Generator

Generates tactical FRAG-O / ATO briefing kneeboards (768x1024 PNG) from campaign save data. Rewrote from Playwright+Chromium to **Pillow only** for speed and CI compatibility.

### Usage
```bash
python briefing.pyw                    # Auto-detect .miz in current dir
python briefing.pyw Foothold.miz       # Specific .miz file
python briefing.pyw Caucasus           # Unpacked directory mode (no .miz needed)
```

### What it does
1. Reads setup script (auto-detects `MA_Setup_*.lua` or any with `bc:addConnection`)
2. Reads `zoneCommander.lua` for zone rename mappings
3. Parses campaign save file from `../Saves/` for live zone state
4. Computes tactical picture: frontline, SEAD targets, attack objectives, capture candidates
5. Renders BLUE and RED briefing PNGs
6. In .miz mode: injects BLUE PNG into kneeboard and creates backup

### Dependencies
- `pip install Pillow` (that's it — no browser, no async)

## The Plan / Roadmap

### Immediate (in progress)
- [x] Monorepo with all 8 theaters organized
- [x] Cross-theater diff and consistency analysis
- [x] Per-theater README.md with notes/issues
- [x] briefing.pyw rewritten with Pillow
- [ ] CI pipeline: auto-repack each theater into `.miz` on push/release
- [ ] CI pipeline: run briefing.pyw per theater as part of build

### Next steps
- [ ] Deep dive: validate `mapResource` references vs actual files per theater
- [ ] Deep dive: cross-check `Foothold Config.lua` defaults vs era-locked maps
- [ ] Deep dive: inspect each map-specific setup script for broken zone references
- [ ] Deep dive: diff `options` files across theaters for gameplay setting inconsistencies
- [ ] Python repack script for CI (zip theater contents → `.miz`, exclude README/briefing PNGs)

### Collaboration with Leka
- Leka has GitHub (1 public repo, 1 private with current files)
- Available weekends only
- Plan: demo the automated workflow, then teach him to use it
- Goal: he updates scripts → pushes → CI builds .miz releases automatically
- His DCS User Files page: https://www.digitalcombatsimulator.com/en/files/filter/user-is-Lekaa/apply/

## Conventions

- Each theater directory maps 1:1 to a `.miz` archive
- `README.md` in each theater is for our notes/observations, excluded from .miz repack
- `briefing_blue.png` / `briefing_red.png` are generated artifacts, excluded from .miz repack
- The Caucasus `README.md` doubles as the comprehensive v2 research document
- Docs/ contains only official PDFs from lekaa (theater-agnostic)
- Never edit upstream shared scripts (Moose, zoneCommander, etc.) — report issues to lekaa

## Credits

- **lekaa** — Foothold Extended mission author
- **Dzsekeb** — Original Foothold concept
- **MOOSE Framework** — Applevangelist
- **Chromium18** — AIEN (AI Enhancement)
- **ciribob** — CTLD and CSAR
- **Discord**: https://discord.gg/cshgmgXuxE
