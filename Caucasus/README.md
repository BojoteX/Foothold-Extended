# Foothold Extended Caucasus — Comprehensive Research Document (v2)
**Version:** v2 — Verified against source files (Foothold Config V1.0.2, MA_Setup_CA.lua, zoneCommander.lua, WelcomeMessage.lua, Zeus.lua, EWRS.lua, AIEN.lua, Foothold CTLD.lua)
**Mission by:** lekaa (Discord: leka86)
**Built upon:** Original Foothold concept by Dzsekeb
**Framework dependencies:** MOOSE scripting framework (Applevangelist), AIEN (Chromium18)
**DCS Version:** 2.9
**Map:** Caucasus
**Mission date:** October 31, 2024 [VERIFIED]
**Config version:** V1.0.2 [VERIFIED]
**Last verified update:** 2026-03-21
**Download:** https://www.digitalcombatsimulator.com/en/files/3341245/
**Community Discord:** https://discord.gg/cshgmgXuxE
**Mission type:** Multiplayer (dedicated server required — will NOT run in single player due to Dynamic Spawn)
**License:** Freeware — Do Not Redistribute

---

## Table of Contents

1. [Mission Overview & Philosophy](#1-mission-overview--philosophy)
2. [Server Requirements & Setup](#2-server-requirements--setup)
3. [Core Concept — The Foothold Loop](#3-core-concept--the-foothold-loop)
4. [Zone System — Capture & Control](#4-zone-system--capture--control)
5. [Persistence System](#5-persistence-system)
6. [Credit / Economy System](#6-credit--economy-system)
7. [Ranking System](#7-ranking-system)
8. [Player Mission Types](#8-player-mission-types)
9. [The Purchase Shop](#9-the-purchase-shop)
10. [AI Systems — Skynet / MANTIS](#10-ai-systems--skynet--mantis)
11. [AI Systems — AIEN Ground Enhancement](#11-ai-systems--aien-ground-enhancement)
12. [AI Systems — Dynamic Aircraft Spawning](#12-ai-systems--dynamic-aircraft-spawning)
13. [AI Systems — RED Reactive Counterpressure](#13-ai-systems--red-reactive-counterpressure)
14. [CTLD — Combat Troop and Logistics Deployment](#14-ctld--combat-troop-and-logistics-deployment)
15. [CSAR — Combat Search and Rescue](#15-csar--combat-search-and-rescue)
16. [Fixed-Wing Escort AI](#16-fixed-wing-escort-ai)
17. [JTAC System](#17-jtac-system)
18. [Joint Missions](#18-joint-missions)
19. [Hunt System](#19-hunt-system)
20. [Warehouse Logistics](#20-warehouse-logistics)
21. [EWRS — Early Warning Radar System](#21-ewrs--early-warning-radar-system)
22. [Zeus Script](#22-zeus-script)
23. [ATIS System](#23-atis-system)
24. [Ships & Carriers](#24-ships--carriers)
25. [Difficulty & Advanced Configuration](#25-difficulty--advanced-configuration)
26. [Cold War Era Mode](#26-cold-war-era-mode)
27. [External Config Override](#27-external-config-override)
28. [Full Zone Map](#28-full-zone-map)
29. [Appendix — Full Config Reference](#29-appendix--full-config-reference)

---

## 1. Mission Overview & Philosophy

Foothold Extended Caucasus is a persistent, multiplayer PvE campaign for DCS World on the Caucasus map. Players fight as the BLUE coalition to liberate zones held by RED AI forces. The mission features a full economy system, AI ground enhancement, logistics, CTLD, CSAR, dynamic AI aircraft spawning scaled to player count, and session-to-session persistence.

The mission is built on multiple scripting layers:
- **MOOSE** — core framework for spawning, tasking, zone management
- **BattleCommander / ZoneCommander** — the Foothold-specific zone ownership and progression system (in `zoneCommander.lua`)
- **AIEN** — AI ground enhancement by Chromium18 (reactions, dismounts, fire missions, initiative)
- **EWRS** — early warning radar system
- **CTLD** — combat troop and logistics deployment (MOOSE-based, heavily customized)
- **Splash Damage** — optional enhanced bomb blast effects

---

## 2. Server Requirements & Setup

- Requires a **dedicated DCS server**; will not work in single player due to Dynamic Spawn.
- Persistence is saved to `Missions/Saves/` within the DCS write directory.
- Zone state save file: `FootHold_CA_v0.2.lua` (Modern) or `FootHold_CA_v0.2_Coldwar.lua` (Cold War) [VERIFIED from MA_Setup_CA.lua line 325]
- Rank data save file: `Missions/Saves/Foothold_Ranks.lua` [VERIFIED from MA_Setup_CA.lua line 526]
- CTLD save frequency: every 10 minutes [VERIFIED — per manual p32]
- Zone save interval: checked every 10 seconds, saved every 60 seconds [VERIFIED from `bc = BattleCommander:new(filepath, 10, 60)` — MA_Setup_CA.lua line 524]

### External Config Override [VERIFIED]

The config file (`Foothold Config.lua`) supports loading from an external path. If a file named `Foothold Config.lua` exists in `Missions\Saves\`, it will be loaded instead of the one embedded in the .miz. This allows server operators to customize settings without editing the mission file. [VERIFIED — Foothold Config.lua lines 12-19]

---

## 3. Core Concept — The Foothold Loop

1. **Spawn** at a friendly zone (Batumi is the starting blue base with infinite warehouse stock via `LogisticCenter = true`)
2. **Earn credits** by destroying enemy units, completing CSAR, delivering CTLD cargo, or capturing zones
3. **Purchase support** from the shop (AI flights, zone upgrades, combined arms, etc.)
4. **Deploy ground forces** via CTLD to capture or upgrade zones
5. **Advance the front line** — zones switch from RED to BLUE as troops overwhelm defenders
6. **Defend** — RED AI reacts dynamically, launches counterattacks, and tries to recapture zones
7. **Persistence** — all progress saves between sessions

---

## 4. Zone System — Capture & Control

### Zone Types [VERIFIED from MA_Setup_CA.lua]

| Category | Zones |
|---|---|
| **Airfields** | Batumi (BLUE start), Kobuleti, Senaki, Kutaisi, Sukhumi, Gudauta, Sochi, Gelendzhik, Novorossiysk, Anapa, Krymsk, Krasnodar-Center, Krasnodar-Pashkovsky, Maykop, Mineralnye, Nalchik, Mozdok, Beslan, Soganlug, Tbilisi, Vaziani |
| **FARPs / FOBs** | Alpha, Bravo, Charlie, Delta, Echo, Foxtrot, Golf, Hotel, India, Juliett, Kilo, Lima |
| **SAM Sites** | SAM-Alpha, SAM-Bravo, SAM-Charlie, SAM-Delta, SAM-Echo, SAM-Foxtrot, SAM-Golf, SAM-Hotel, SAM-India, SAM-Juliett, SAM-Kilo, SAM-Lima, SAM-Mike, SAMSite |
| **Strategic Targets** | MiningFacility, TankFactory, InsurgentCamp, ChemSite, SecretTechFacility, ArtilleryFactory, FuelDepo, AmmonitionDepo |
| **Ship Zones** | Red Carrier, Blue Carrier |
| **Hidden Zones** | Hidden (neutral), Hidden1 (red), Hidden2 (neutral), Hidden3 (neutral) |

### Zone Sizes [VERIFIED]

Zones are assigned size templates that determine the composition of AI defenders via randomized upgrade templates:

| Size | SAM | SHORAD | AAA | Ground | Armor | Arty | Total Range |
|---|---|---|---|---|---|---|---|
| small | 0 | 1-2 | 2 | 1 | 1-2 | 0-1 | 5-7 |
| smallmedium | 0 | 1-3 | 2 | 1 | 1-2 | 0-1 | 6-8 |
| medium | 0-1 | 1-3 | 1-3 | 1 | 1-2 | 1 | 7-9 |
| mediumbig | 0-1 | 2-3 | 1-2 | 1 | 2 | 1 | 7-10 |
| big | 1 | 2-3 | 1-2 | 1 | 2 | 1 | 8-10 |
| bignosam | 0 | 3-4 | 1-2 | 1 | 2 | 1 | 7-10 |
| extrabig | 2 | 3-4 | 2 | 1 | 1-2 | 1 | 10-12 |
| sam | 1 | 1-2 | 1-2 | 0 | 0 | 0 | 5 |
| sam2 | 1 | 1-2 | 1-2 | 0 | 0-1 | 0 | 5-6 |
| samspecial | 2 | 1-3 | 1-2 | 0 | 0 | 0 | 6-7 |

### Zone Capture Mechanics

- Zones can be captured by deploying troops (CTLD) into enemy zones
- The shop `capture` item (500cr, Rank 1) can capture neutral zones
- `CaptureZoneWithEngineer` (default: false) controls whether engineer soldiers can capture/upgrade zones [VERIFIED]
- Zones start at side RED (side=1) except Batumi (side=2, BLUE start) and hidden zones (side=0, neutral)
- Each zone has a waypoint number for navigation (Batumi=2 through Vaziani=34) [VERIFIED from WaypointList]

---

## 5. Persistence System

### What Persists

- **Zone ownership and state** — saved to `FootHold_CA_v0.2.lua` every 60 seconds [VERIFIED]
- **Player ranks** — saved to `Foothold_Ranks.lua` [VERIFIED]
- **CTLD-deployed units** — saved every 10 minutes, with limits per unit type via `MAX_AT_SPAWN` [VERIFIED]
- **FARPs** — up to `MAX_SAVED_FARPS = 3` [VERIFIED — Foothold Config.lua line 529]
- **Tanker positions** — persistent/saved
- **Warehouse state** — when `WarehouseLogistics = true` (default)

### MAX_AT_SPAWN — Units Loaded From Save [VERIFIED — Foothold Config.lua lines 499-527]

| Unit | Max Saved |
|---|---|
| Engineer soldier | 0 |
| Squad 8 | 0 |
| Platoon 16 | 0 |
| Platoon 32 | 0 |
| Mephisto | 2 |
| Humvee | 2 |
| Bradly | 2 |
| L118 | 3 |
| Ammo Truck | 3 |
| Humvee scout | 1 |
| Anti-Air Soldiers | 2 |
| Mortar Squad | 2 |
| Linebacker | 2 |
| Vulcan | 2 |
| HAWK Site | 3 |
| Nasam Site | 3 |
| Tank Abrahams | 0 |
| FARP | 3 |
| IRIS T STR Add-on | 3 |
| IRIS T LN Add-on | 8 |
| IRIS T C2 Add-on | 3 |
| IRIS T System | 2 |
| C-RAM | 4 |
| HIMARS GMLRRS HE GUIDED | 4 |
| FV-107 Scimitar | 2 |
| FV-101 Scorpion | 2 |
| Avenger | 2 |

---

## 6. Credit / Economy System

### Earning Credits [VERIFIED — Foothold Config.lua lines 263-275]

Credits are earned per kill by target type (`RewardContribution`):

| Target Type | Credits |
|---|---|
| Infantry | 10 |
| Ground | 10 |
| SAM | 30 |
| Airplane | 50 |
| Helicopter | 50 |
| Ship | 200 |
| Crate (CTLD delivery) | 100 |
| Rescue (CSAR) | 200 |
| Zone upgrade | 100 |
| Zone capture | 200 |
| Structure | 100 |

### Credit Claiming Rules [VERIFIED — from dictionary file]

- Credits are **not** instantly added to the coalition account. The player must **land at a friendly zone** to claim accumulated credits.
- **Ejecting** claims only **25%** of accumulated credits (the pilot loses 75%).
- **CSAR recovery** of an ejected player: the rescuer earns 200 credits for the rescue itself, plus recovers the 75% credits the ejected pilot lost. AI pilot CSAR payout is capped at 300.

### Credit/Rank Loss on Death [VERIFIED — Foothold Config.lua lines 174-183]

| Setting | Default | Amount |
|---|---|---|
| `CreditLosewhenKilled` | `false` | 100 credits lost from coalition pool |
| `CreditLosewhenKilledAmount` | 100 | Configurable |
| `RankLoseWhenKilled` | `true` | 100 rank credits lost from personal rank |
| `RankLoseWhenKilledAmount` | 100 | Configurable |

### Flight Time Rewards [VERIFIED — Foothold Config.lua lines 386-424]

- `RewardFlightTime` = `true` (default) — pilots earn credits per minute airborne
- `FlightTimeRewardPerMinute` = 2 (default)
- Counting starts after 5 minutes airborne; the first 5 minutes are retroactively counted
- `RewardAllAircraft` = `false` — by default, only specific aircraft earn flight time rewards
- Default allowed aircraft for flight time rewards: C-130J-30, CH-47F, Hercules (all others set to false)

### Friendly Fire Penalty [VERIFIED]

- `FriendlyFireRankPenalty` = 500 rank credits [VERIFIED — Foothold Config.lua line 202]

---

## 7. Ranking System

### Rank Titles & Thresholds [VERIFIED — zoneCommander.lua line 4855-4856]

| Rank Level | Title | Score Threshold |
|---|---|---|
| 1 | Recruit | 0 |
| 2 | Aviator | 3,000 |
| 3 | Airman | 5,000 |
| 4 | Senior Airman | 8,000 |
| 5 | Staff Sergeant | 12,000 |
| 6 | Technical Sergeant | 16,000 |
| 7 | Master Sergeant | 22,000 |
| 8 | Senior Master Sergeant | 30,000 |
| 9 | Chief Master Sergeant | 45,000 |
| 10 | Second Lieutenant | 65,000 |
| 11 | First Lieutenant | 90,000 |

- `RankingSystem` = `true` (default) — enables rank-gated shop access [VERIFIED]
- If `RankingSystem` = `false`, everyone can access the full shop

### StoreLimit [VERIFIED — Foothold Config.lua lines 191-196]

Optional additional credit-gated shop access (`StoreLimit` = `false` by default):
- Items costing > 250 require 100 earned credits
- Items costing > 1000 require 1,000 earned credits
- Items costing > 2000 require 2,000 earned credits
- Items costing > 3000 require 3,000 earned credits

---

## 8. Player Mission Types

### Joint Missions [VERIFIED — zoneCommander.lua line 21854-21860]

Two players can team up for double mission credit rewards:
1. Host selects "Invite to joint mission" to receive a **4-digit code**
2. Teammate opens "Join another player" and enters the code
3. Credits are rewarded to both for missions (not regular kills)
4. Valid for: **CAP, CAS, Bomb Runway, Strike** missions [VERIFIED]

### Bomb Runway Mission [VERIFIED]

- Prevents enemy planes from taking off at a target airbase
- Selects the best target based on which enemy airbase has the most planes (CAP planes score higher)
- Each runway must be bombed separately for multi-runway bases
- Runway strike templates: `RED_MIG-27K_RUNWAY`, `RED_SU-33_RUNWAY` (Modern), `RED_MIRAGE_F1_RUNWAY` [VERIFIED]

---

## 9. The Purchase Shop

### Shop Prices [VERIFIED — Foothold Config.lua lines 278-312]

| Item | Price | Rank Required | Category |
|---|---|---|---|
| Smoke markers | 20 | 1 | Marking & Tools |
| Flare markers | 20 | 1 | Marking & Tools |
| Illumination bomb | 100 | 1 | Marking & Tools |
| Capture neutral zone | 500 | 1 | Capture & Resources |
| Resupply friendly zone | 200 | 1 | Capture & Resources |
| Logistics center (zone) | 2,000 | 1 | Capture & Resources |
| Resupply warehouse +50 | 500 | 2 | Zone Upgrades |
| MQ-9 Reaper JTAC | 500 | 2 | JTAC & Intel |
| JTAC 9-Line AM | 0 | 1 | JTAC & Intel |
| JTAC 9-Line FM | 0 | 1 | JTAC & Intel |
| CAP Flight | 500 | 2 | AI Attack |
| TALD Decoy Flight | 300 | 2 | AI Attack |
| Deploy recon group | 50 | 3 | Combined Arms |
| Deploy armor | 100 | 3 | Combined Arms |
| Deploy artillery | 100 | 3 | Combined Arms |
| Deploy air defence | 150 | 3 | Combined Arms |
| Dynamic Tanker (Drogue/ARCO) | 1,000 | 3 | AI Attack |
| Dynamic Tanker (Boom/TEXACO) | 1,000 | 3 | AI Attack |
| SEAD Flight | 500 | 4 | AI Attack |
| Bomber Flight | 500 | 4 | AI Attack |
| Static Structure Strike | 500 | 4 | AI Attack |
| Deploy FARP | 1,000 | 4 | Capture & Resources |
| Jam radars at zone | 500 | 4 | Other Support |
| CAS Flight | 1,000 | 5 | AI Attack |
| Intel on enemy zone | 150 | 5 | JTAC & Intel |
| Add infantry squad to zone | 500 | 5 | Zone Upgrades |
| Fully upgrade friendly zone | 1,000 | 6 | Capture & Resources |
| Add HAWK/NASAMS to zone | 2,000 | 6 | Zone Upgrades |
| Add armor group to zone | 1,000 | 7 | Zone Upgrades |
| Add Patriot to zone | 5,000 | 8 | Zone Upgrades |
| Add HIMARS to zone | 2,500 | 8 | Zone Upgrades |
| Unlock extra upgrade slot | 3,000 | 9 | Zone Upgrades |
| Cruise missile strike | 800 | 10 | AI Attack |

### Shop Category Labels [VERIFIED — Foothold Config.lua lines 353-371]

Display order:
1. AI Attack
2. Zone Upgrades
3. JTAC & Intel
4. Marking & Tools
5. Combined Arms
6. Capture & Resources
7. Other Support

### Tankers [VERIFIED]

- Tankers are **purchasable** (1,000cr each, Rank 3) — not progression-unlocked
- `TexacoSpeed` = 286 knots, `ArcoSpeed` = 286 knots [VERIFIED — Foothold Config.lua lines 622-624]
- Tanker position is persistent/saved

### AI Attack Options [VERIFIED — Foothold Config.lua lines 373-379]

- `AIAttackTakeoffFromGround` = `true` (default) — AI attack groups take off from ground rather than airspawning
- `AIAttackTakeoffFromGroundExtraNM` = 40
- `AllowScriptedSupplies` = `false` — purchased supply upgrades are delivered by helicopter, not instant

---

## 10. AI Systems — Skynet / MANTIS

The mission uses the Skynet/MANTIS IADS (Integrated Air Defense System) framework for SAM coordination:

- `HideSAMOnMFD` = `true` (default) — SAMs are hidden on player MFDs [VERIFIED]
  - `false` = always shown
  - `true` = always hidden
  - `"random"` = 50% chance hidden per spawn

### SAM Sites in Mission [VERIFIED from MA_Setup_CA.lua upgrades table]

| Zone Key | SAM Systems Present |
|---|---|
| samalphaFixed | SA-15, SA-2, SA-3 |
| sambravoFixed | SA-15, SA-2 |
| samcharliefixed | SA-15, SA-19, SA-6 |
| samdeltaFixed | SA-19, SA-10 |
| SAMEcho | SA-15, SA-11, Pantsir S1 |
| samFoxtrotFixed | SA-19, SA-2 |
| samgolf | SA-6, SA-19, SA-15 |
| sam3 (Hotel) | SA-15, SA-6, SA-8 |
| sam4indiafixed | SA-19, SA-8, SA-15, SA-10 |
| sam4kilofixed | SA-15, SA-10 |
| sam5 (Juliett/SAMSite) | SA-15, SA-8, SA-11 |
| SamLimaFixedSA11 | SA-15, SA-6, SA-11 |
| sam6 (Mike) | SA-19, SA-5 |

### SAM Replacement Options [VERIFIED — Foothold Config.lua lines 157-165]

- `NoSA10AndSA11` = `false` — if true, SA-10 and SA-11 replaced by random older SAMs (SA-2, SA-3, SA-6)
- `NoTorM2AndPantsir` = `false` — if true, Pantsir and Tor M2 replaced by random SHORAD (SA-19, SA-8, SA-13, SA-9)
- `NoSA15` = `false` — if true, SA-15 replaced by random SHORAD (SA-19, SA-8, SA-13, SA-9)

---

## 11. AI Systems — AIEN Ground Enhancement

AIEN (by Chromium18) enhances ground AI behavior with reactions, suppression, dismounts, fire missions, and initiative. [VERIFIED — AIEN.lua]

### Configurable Toggles [VERIFIED — Foothold Config.lua lines 783-799]

| Setting | Default | Description |
|---|---|---|
| `AIEN.config.dontInitialize` | `false` | Disable AIEN entirely |
| `AIEN.config.blueAI` | `true` | Apply AI enhancement to blue coalition ground groups |
| `AIEN.config.redAI` | `true` | Apply AI enhancement to red coalition ground groups |
| `AIEN.config.dismount` | `true` | Trucks/APCs dismount troops when hit but not killed |
| `AIEN.config.message_feed` | `true` | Show coalition messages when AI acts |
| `AIEN.config.initiative` | `true` | AI ground groups take initiative to move toward detected enemies |

### AIEN Features (from AIEN.lua)

- **Fire missions** — artillery units automatically fire at targets provided by other ground units and drones
- **UAV night scan** — UAVs supplement detection when visibility-based sensors fail
- **Reactions** — when hit, groups react according to skill and situational awareness
- **Suppression** — non-armored groups under fire are suppressed for 15-45 seconds
- **Dismount** — APCs/IFVs/trucks dismount soldiers with rifles, RPGs, and sometimes MANPADs
- **Initiative** — groups advance toward detected enemies within tactical range (4000m)
- **Counter-battery** — radar-capable units calculate counter-battery fire (50,000m radar range)
- **Blue hit reactions** limited to artillery support/counter-battery only (`blueHitFireSupportOnly = true`)

### Performance Tuning [VERIFIED — Foothold Config.lua lines 797-799]

| Timer | Default | Purpose |
|---|---|---|
| `phaseCycleTimerMin` | 0.2 | Initialization cadence |
| `phaseCycleTimerActive` | 0.04 | Runtime cadence when work pending |
| `phaseCycleTimerIdle` | 0.5 | Relaxed cadence when idle |

---

## 12. AI Systems — Dynamic Aircraft Spawning

AI aircraft (CAP, CAS, SEAD, Helo CAS, Supply, Runway Strike) are dynamically spawned based on player count and difficulty settings.

### Player Count Ignore Lists [VERIFIED — Foothold Config.lua lines 596-616]

Aircraft types excluded from player count for scaling purposes:

**CAP count ignores** (`CapCountIgnoreTypes`): A-10C_2, Hercules, A-10A, A-10C, AV8BNA, AJS37, C-130J-30 [VERIFIED]

**Blue CAS count ignores** (`BlueCasCountIgnoreTypes`): Hercules, C-130J-30, CH-47Fbl1 [VERIFIED]

**Red CAS count ignores** (`RedCasCountIgnoreTypes`): Hercules, C-130J-30, CH-47Fbl1 [VERIFIED]

### CAP Scaling Stages [VERIFIED — Foothold Config.lua lines 634-667]

**Red CAP Limits (`CapLimitStages`):**

| Players | Easy | Medium | Hard |
|---|---|---|---|
| 0 | 0 | 1 | 1 |
| 1 | 1 | 1 | 2 |
| 2 | 2 | 3 | 4 |
| 3 | 3 | 4 | 4 |
| 4 | 3 | 4 | 5 |
| 5 | — | 4 | 5 |
| 9 | 4 | 5 | 6 |
| 10 | 5 | 6 | 7 |
| 999 | 6 | 7 | 8 |

**Red CAS/SEAD Limits (`RedCasLimitStages`):**

| Players | Easy | Medium | Hard |
|---|---|---|---|
| 0 | 0 | 1 | 1 |
| 1 | 0 | 1 | 2 |
| 2 | 1 | 1 | 2 |
| 3 | 1 | 2 | 3 |
| 4 | 2 | 3 | 4 |
| 5 | 2 | 3 | 4 |
| 9 | — | 4 | 6 |
| 999 | 3 | 4 | 7 |

**Blue CAP/CAS/SEAD Support Limits** (all three use the same structure):

| Players | Easy | Medium | Hard |
|---|---|---|---|
| 0 | 2 | 1 | 0 |
| 1 | 2 | 1 | 0 |
| 999 | 1 | 0 | 0 |

### AI Skill Settings [VERIFIED — Foothold Config.lua lines 62-68]

- `AiPlaneSkill` = `"Random"` — for spawned Red airplanes
- `AiGroundSkill` = `"Excellent"` — for spawned ground units (shared Red/Blue)
- Valid values: "Average", "Good", "High", "Excellent", "Random"

### Aircraft Templates [VERIFIED from MA_Setup_CA.lua]

**Modern Era CAP:** MiG-29S, MiG-29A, Su-27, MiG-21Bis, MiG-23MLD, MiG-25PD (RED); F/A-18C, F-15C, F-16C, F-14B, M-2000C (BLUE)

**Modern Era CAS:** Su-25, Su-25T, Mirage F1BQ, MiG-21Bis (RED); F-4E (BLUE)

**Modern Era SEAD:** JF-17, Su-25T, Su-34, Su-24M (RED)

**Modern Era CAS Helo:** Mi-24P, Mi-28N (RED); AH-64D, AH-1W, SA342M, OH-58D (BLUE)

---

## 13. AI Systems — RED Reactive Counterpressure

When BLUE players get close to RED frontline zones, RED reacts with two mechanisms: [VERIFIED — Foothold Config.lua lines 78-139]

1. **Soft reaction** — RED speeds up supply and CAP groups for pressured zones
2. **Hard reaction** — RED force-spawns attack groups to strike BLUE zones

The active profile is determined by the higher of `CapDifficulty` and `CasSeadDifficulty`.

### Profile Comparison [VERIFIED]

| Parameter | Easy | Medium | Hard |
|---|---|---|---|
| Enabled | No | Yes | Yes |
| Min pressure (soft) | 16 | 10 | 6 |
| Min pressure (hard) | 15 | 12 | 12 |
| Capture hard window | 120s | 180s | 240s |
| Hard zone cooldown | 1800s | 1800s | 900s |
| Max zones per tick | 1 | 1 | 2 |
| Supply boost/zone | 0 | 1 | 1 |
| CAP boost/zone | 0 | 1 | 1 |
| CAP boost cooldown | 1800s | 1500s | 900s |
| Hard force/zone | 1 | 1 | 2 |
| Hard force total/tick | 1 | 1 | 2 |
| Group reuse cooldown | 1600s | 1200s | 900s |

---

## 14. CTLD — Combat Troop and Logistics Deployment

### CTLD Configuration [VERIFIED — Foothold CTLD.lua lines 1-46]

| Setting | Value |
|---|---|
| `dropcratesanywhere` | `true` |
| `forcehoverload` | `false` |
| `CrateDistance` | 65m |
| `PackDistance` | 65m |
| `maximumHoverHeight` | 20m |
| `minimumHoverHeight` | 3m |
| `smokedistance` | 8000m |
| `enableFixedWing` | `true` |
| `FixedMinAngels` | 100m (~470ft) |
| `FixedMaxSpeed` | 200 (77 m/s / 150kn) |
| `dropAsCargoCrate` | `true` |
| `enableslingload` | `true` |
| `pilotmustopendoors` | `true` |
| `buildtime` | 30 seconds |
| `UseC130LoadAndUnload` | `true` (default) |

### Per-Airframe CTLD Capabilities [VERIFIED — Foothold Config.lua lines 450-467]

| Airframe | Can Crates | Can Troops | Max Crates | Max Troops | Max Cargo (kg) |
|---|---|---|---|---|---|
| SA342 (all variants) | No | Yes | 0 | 2 | 400 |
| UH-1H | Yes | Yes | 1 | 8 | 800 |
| Mi-8MT | Yes | Yes | 3 | 16 | 6,000 |
| Mi-8MTV2 | Yes | Yes | 3 | 18 | 6,000 |
| Ka-50 | No | No | 0 | 0 | 400 |
| Mi-24P / Mi-24V | Yes | Yes | 2 | 8 | 1,000 |
| C-130J-30 | Yes | Yes | 7 | 64 | 21,500 |
| UH-60L / UH-60L DAP | Yes | Yes | 2 | 20 | 3,500 |
| AH-64D | No | No | 0 | 0 | 400 |
| CH-47F | Yes | Yes | 5 | 32 | 10,800 |
| OH-58D | No | No | 0 | 0 | 400 |

### CTLD Unit Prices [VERIFIED — Foothold Config.lua lines 470-497]

| Unit | Price | Rank Required | Era |
|---|---|---|---|
| Engineer soldier | 50 | 1 | All |
| Squad 8 | 50 | 1 | All |
| Platoon 16 | 100 | 1 | All |
| Platoon 32 | 200 | 1 | All |
| Anti-Air Soldiers | 100 | 1 | All |
| Mortar Squad | 100 | 1 | All |
| Humvee | 250 | 1 | All |
| Bradly | 250 | 1 | All |
| L118 (artillery) | 150 | 1 | All |
| Ammo Truck | 100 | 1 | All |
| Humvee scout | 100 | 1 | All |
| FARP | 500 | 1 | All |
| Mephisto | 250 | 2 | All |
| Linebacker | 300 | 2 | All |
| Vulcan | 300 | 2 | All |
| C-RAM | 500 | 2 | Modern only |
| FV-107 Scimitar | 250 | 2 | All |
| FV-101 Scorpion | 250 | 2 | All |
| Avenger | 250 | 2 | All |
| HAWK Site | 750 | 3 | All |
| Nasam Site | 750 | 3 | All |
| IRIS T STR Add-on | 750 | 3 | Modern only |
| IRIS T LN Add-on | 500 | 3 | Modern only |
| IRIS T C2 Add-on | 500 | 3 | Modern only |
| IRIS T System | 1,800 | 3 | Modern only |
| HIMARS GMLRRS HE GUIDED | 1,000 | 3 | Modern only |

### CTLD Cost Toggle [VERIFIED]

- `CTLDCost` = `true` (default) — CTLD crates/units cost credits
- If `false`, CTLD is free

### IRIS Merge Behavior [VERIFIED — Foothold Config.lua lines 532-535]

- `IRIS_RESTORE_UNIT_HEALTH_ON_MERGE` = `false` (default)
- `true` = merge from full template (destroyed IRIS units can come back)
- `false` = merge from currently alive IRIS composition + new unit

---

## 15. CSAR — Combat Search and Rescue

### CSAR Capacity Per Airframe [VERIFIED — Foothold Config.lua lines 544-565]

| Airframe | Max Pilots |
|---|---|
| Ka-50 / Ka-50_3 | 0 |
| Mi-24P | 8 |
| SA342 (all variants) | 3 |
| UH-60L / UH-60L DAP | 11 |
| UH-1H | 11 |
| Mi-8MT | 24 |
| AH-64D | 2 |
| OH-58D | 1 |
| CH-47F | 32 |
| Bronco OV-10A | 5 |
| OH-6A | 2 |
| MH-6J | 4 |
| AH-6J | 4 |
| C-130J-30 | 0 |
| Hercules | 0 |

### CSAR Parameters [VERIFIED — Foothold Config.lua lines 568-581]

| Setting | Value |
|---|---|
| `PilotWeight` | 80 kg |
| `CsarHoverDistance` | 20m from survivor |
| `CsarHoverHeight` | 60m AGL |
| `CsarHoverSeconds` | 10 seconds |
| `CsarHostileInfantryChance` | 25% |

---

## 16. Fixed-Wing Escort AI

### Eligible Aircraft [VERIFIED — WelcomeMessage.lua line 1656]

Escort is available for: **A-10C_2**, **F-15ESE (F-15E Strike Eagle)**, **Hercules**, and **C-130J-30**

### Escort Details [VERIFIED — WelcomeMessage.lua lines 1397-1414]

- Escort consists of 2x F/A-18C (from MOOSE AUFTRAG escort template)
- Escort flies at an offset position: `{x = -100, y = 3048, z = 100}` — approximately **10,000ft above** the player [VERIFIED — 3048m = 10,000ft]
- Engagement radius: **40 NM** [VERIFIED — `escortAuftrag = AUFTRAG:NewESCORT(clientGroup, { x = -100, y = 3048, z = 100 }, 40, { "Air" })`]
- Escort has unlimited fuel
- `EscortTakeoffFromGround` = `true` (default) — escort takes off from nearest friendly airbase rather than airspawning [VERIFIED]
- If spawning from ground, escort announces scramble and joins player after takeoff
- Cold War era uses different templates (`EscortA10_Coldwar`, `EscortF15_Coldwar`)

### Escort Menu Commands

After escort spawns, players get control menus via the F10 radio menu (managed by MOOSE AUFTRAG/FLIGHTGROUP).

---

## 17. JTAC System

### MQ-9 Reaper JTAC [VERIFIED — zoneCommander.lua]

- Default laser code: **1688** [VERIFIED — zoneCommander.lua line 1594]
- Laser code can be changed to any value between 1111 and 1788
- Cost: 500 credits (Rank 2) [VERIFIED]

### JTAC Priority Categories [VERIFIED — zoneCommander.lua lines 1575-1582]

| Priority | Target Types |
|---|---|
| SAM | SAM SR, SAM TR, IR Guided SAM |
| Structures | StaticObjects (only when `UseStatics = true`) |
| Infantry | Infantry |
| Armor | Tanks, IFV, APC |
| Support | Unarmed vehicles, Artillery, SAM LL, SAM CC |

### Self-JTAC (SelfJtac) [VERIFIED — zoneCommander.lua line 19465+]

Players can also use a self-JTAC system from their own aircraft with the same laser code and priority system. Default code: 1688.

### JTAC 9-Line [VERIFIED]

- 9-Line AM and FM are available as free shop items (0 credits, Rank 1)
- These provide target information via the AIEN fire mission system

---

## 18. Joint Missions

Players can team up for shared mission rewards: [VERIFIED — zoneCommander.lua line 21854-21860]

1. Host selects "Invite to joint mission" and receives a **4-digit code**
2. Teammate opens "Join another player" and enters the code
3. Both players earn credits for completed missions (not regular kills)
4. Valid mission types: **CAP, CAS, Bomb Runway, Strike**

---

## 19. Hunt System

The hunt system targets players who repeatedly bomb zones: [VERIFIED — MA_Setup_CA.lua lines 3825-3826, zoneCommander.lua lines 11447-11610]

- The hunt threshold is **randomized per session**: between 6-15 kills (or 8-15 if SplashDamage is enabled) [VERIFIED — `math.random(6,15)` / `math.random(8,15)`]
- Once a player exceeds the threshold, RED dispatches **2 jets** to hunt them specifically
- Player receives the message: "Enemy is scrambling 2 jets to hunt you down!" and hears the audio cue "Watch your six"
- `Hunt = true` is hardcoded in MA_Setup_CA.lua [VERIFIED]
- The hunter jets spawn from the nearest eligible RED airbase (minimum 15 NM from player, preferred 30+ NM)
- The system tracks kills per player name and marks players as "done" after being hunted once

---

## 20. Warehouse Logistics

### Core Warehouse System [VERIFIED — Foothold Config.lua lines 216-235]

| Setting | Default | Description |
|---|---|---|
| `WarehouseLogistics` | `true` | Logistics via warehouse + zone supplies only |
| `AIDeliveryamount` | 20 | Units delivered per AI supply run |
| `AutoFillResources` | 5 | Items auto-added to blue zones every 15 minutes |
| `NoAIBlueSupplies` | `false` | If true, only players deliver supplies |
| `StrictSmartWeaponsInventory` | `false` | If true, smart weapons are half quantity |

### How It Works

- When `WarehouseLogistics = true`, captured zones start with **no weapons**
- Supplies must be brought in via player transport, AI delivery, or auto-fill
- Zone supplies carry 10 of everything
- AI delivers 20 of everything per supply run
- Auto-refill: 5 items every 15 minutes
- The first homebase marked `[WH]` (Batumi with `LogisticCenter = true`) has **infinite stock** [VERIFIED]
- Players can purchase a logistics center (2,000cr, Rank 1) via the shop (`zlogc`) to grant infinite stock to another zone

### AllowMods [VERIFIED — Foothold Config.lua lines 168-171]

- `AllowMods` = `false` (default) — if true, modded weapons fill via warehouse logistics
- Should NOT be used with Cold War era
- Adding mods mid-session while a save file exists means those weapons won't be added to saved airbases; they will fill through AutoFillResources over time

---

## 21. EWRS — Early Warning Radar System

Full EWRS configuration is exposed in `Foothold Config.lua` lines 752-777: [VERIFIED]

| Setting | Default | Description |
|---|---|---|
| `ewrs_messageUpdateInterval` | 60s | How often BRA messages update |
| `ewrs_messageDisplayTime` | 15s | How long messages display |
| `ewrs_restrictToOneReference` | `false` | Lock BRA reference to one option |
| `ewrs_defaultReference` | `"self"` | Default BRA reference (self or bulls) |
| `ewrs_defaultMeasurements` | `"imperial"` | Default measurement units |
| `ewrs_defaultShowTankers` | `false` | Show tankers in picture report |
| `ewrs_disableFightersBRA` | `false` | Disable BRA for fighters |
| `ewrs_enableRedTeam` | `true` | Enable EWRS for red team |
| `ewrs_enableBlueTeam` | `true` | Enable EWRS for blue team |
| `ewrs_disableMessageWhenNoThreats` | `true` | Suppress "no threats" messages |
| `ewrs_useImprovedDetectionLogic` | `true` | Realistic detection with unknowns |
| `ewrs_onDemand` | `false` | F10 menu only (no auto messages) |
| `ewrs_maxThreatDisplay` | 5 | Max threats on picture report |
| `ewrs_allowBogeyDope` | `true` | Allow bogey dope requests |
| `ewrs_allowFriendlyPicture` | `true` | Allow friendly aircraft picture |
| `ewrs_maxFriendlyDisplay` | 5 | Max friendlies shown |
| `ewrs_showType` | `true` | Show unit type |

### EWRS Range Options [VERIFIED]

- km: 10, 20, 40, 60, 80, 100, 150
- nm: 5, 10, 20, 40, 60, 80, 100

### Special Plane Types (always show friendlies) [VERIFIED]

F-4E-45MC, MiG-29 Fulcrum, F-5E-3_FC, C-130J-30

---

## 22. Zeus Script

The Zeus script allows server admins to spawn and manage units via **map markers** (not a GameMaster slot). [VERIFIED — Zeus.lua]

### Usage

1. Place a map marker at the desired location
2. Type a command starting with `-` in the marker text
3. The marker is automatically removed after the command executes

### Commands [VERIFIED — Zeus.lua lines 15-91]

| Command | Effect |
|---|---|
| `-create <unit>` | Spawn a unit at marker location |
| `-destroy1` | Destroy all units within 500m |
| `-destroy2` / `-destroy3` | Destroy all units within 1000m |
| `-destroy4` | Clear all units within 10,000m |
| `-explode <power> [delay]` | Create explosion (default power 100) |
| `-smoke <color>` | Create smoke (red/blue/green/orange/white) |

### Spawnable Units [VERIFIED — Zeus.lua lines 16-19]

SA-8, SA-9, SA-13, SA-15, SA-19, Soldier, Truck, Shilka, Igla, Igla-S, RPG, BMP2, Tank, BTR80, JTAC9lineam, JTAC9linefm, Tankm1, CTLD_CARGO_L118, CTLD_CARGO_Scout

---

## 23. ATIS System

The mission includes an ATIS (Automatic Terminal Information Service) system built in WelcomeMessage.lua. It provides weather and airfield information via the F10 radio menu for all helipad/airfield zones. The system auto-discovers zones from the Foothold zone data.

---

## 24. Ships & Carriers

### Blue Carrier Group [VERIFIED — from dictionary file]

| Ship | Frequency | TACAN | ICLS |
|---|---|---|---|
| CVN-72 Abraham Lincoln | 272 AM | 72X | 12 |
| CVN-74 John C. Stennis | 274 AM | 74X | 14 |

### Red Carrier Group [VERIFIED]

| Ship | Frequency | TACAN | ICLS |
|---|---|---|---|
| CVN-73 George Washington | 273 AM | 73X | 13 |
| CVN-59 Forrestal | 259 AM | 59X | 9 |
| Tarawa | 271.50 AM | 1X | — |

### Additional Ships [VERIFIED — Foothold CTLD.lua line 262]

- HMS Invincible (CTLD zone, ship type)

---

## 25. Difficulty & Advanced Configuration

### Difficulty Scaling [VERIFIED — Foothold Config.lua lines 28-56]

| Setting | Default | Description |
|---|---|---|
| `GlobalSettings.difficultyScaling` | `{[1]=1.0, [2]=1.0}` | Non-supply spawn speed multiplier per coalition. <1.0 = faster, >1.0 = slower |
| `GlobalSettings.supplyDifficultyScaling` | `{[1]=1.0, [2]=1.0}` | Supply-only spawn speed multiplier |
| `CapDifficulty` | `"medium"` | Red CAP quantity |
| `CasSeadDifficulty` | `"medium"` | Red CAS/SEAD/Strike quantity |
| `FriendlyCapSupport` | `"medium"` | Blue CAP support limit |
| `FriendlyCasSupport` | `"medium"` | Blue CAS support limit |
| `FriendlySeadSupport` | `"medium"` | Blue SEAD support limit |

### Mission Rules [VERIFIED — Foothold Config.lua lines 141-213]

| Setting | Default | Description |
|---|---|---|
| `UseStatics` | `true` | Include static targets at certain zones |
| `PVE_Only` | `false` | If true, players cannot spawn in red coalition |
| `Era` | `"Modern"` | "Modern" or "Coldwar" |
| `SplashDamage` | `false` | Enhanced bomb blast effects (may cause stutters) |
| `ShowKills` | `false` | Show Foothold kill messages |
| `InvisibleA10` | `false` | A-10 invisible to RED enemy planes |
| `UseC130LoadAndUnload` | `true` | C-130J-30 and Chinook use internal loading system |

### Forbidden Weapons [VERIFIED — Foothold Config.lua lines 918-921]

`ForbiddWeaponsInAllEra` disables the following in all eras:
- `weapons.bombs.RN-24` (MiG-21 nuclear bomb)
- `weapons.bombs.RN-28` (MiG-21 nuclear bomb)

---

## 26. Cold War Era Mode

Setting `Era = "Coldwar"` activates the Cold War mode which:

- Removes modern weapons from warehouses (extensive `restrictedWeapons` list including AIM-120, JDAM, etc.) [VERIFIED]
- Swaps modern armor/SAM templates for period-appropriate alternatives [VERIFIED — MA_Setup_CA.lua cwSwap table]
- Replaces Pantsir S1 and Tor M2 with random period SAMs (SA-19, SA-8, SA-13, SA-9, SA-15)
- Replaces modern armor groups with Cold War variants
- Uses different aircraft templates for CAP/CAS/SEAD
- Allowed planes list is curated for the era [VERIFIED — Foothold Config.lua `allowedPlanes` table]
- Save file uses different name: `FootHold_CA_v0.2_Coldwar.lua`
- Some features are Modern-only: IRIS T system, C-RAM, HIMARS

---

## 27. External Config Override

The config system supports external override without editing the .miz file: [VERIFIED — Foothold Config.lua lines 12-19]

1. Copy `Foothold Config.lua` to `<DCS Write Dir>\Missions\Saves\Foothold Config.lua`
2. Edit the external copy with desired settings
3. On mission load, the external file is detected and loaded instead of the embedded config
4. A message "Loaded Foothold config externally." is displayed for 30 seconds

---

## 28. Full Zone Map

### All Zones by Category [VERIFIED from MA_Setup_CA.lua zones table]

**Airfields (21 total, all with airbaseName):**
Batumi (BLUE start, LogisticCenter), Kobuleti, Senaki, Kutaisi, Sukhumi, Gudauta, Sochi, Gelendzhik, Novorossiysk, Anapa, Krymsk, Krasnodar-Center, Krasnodar-Pashkovsky, Maykop, Mineralnye, Nalchik, Mozdok, Beslan, Soganlug, Tbilisi, Vaziani

**FARP/FOB Zones (12 total):**
Alpha (FOB), Bravo, Charlie, Delta, Echo (FOB), Foxtrot, Golf (FOB), Hotel, India, Juliett, Kilo, Lima

**SAM Zones (14 total):**
SAM-Alpha, SAM-Bravo, SAM-Charlie, SAM-Delta, SAM-Echo, SAM-Foxtrot, SAM-Golf, SAM-Hotel, SAM-India, SAM-Juliett, SAM-Kilo, SAM-Lima, SAM-Mike, SAMSite

**Strategic Target Zones (8 total):**
MiningFacility, TankFactory, InsurgentCamp, ChemSite, SecretTechFacility, ArtilleryFactory, FuelDepo, AmmonitionDepo

**Ship Zones (2):**
Red Carrier (CVN-73), Blue Carrier (CVN-72)

**Hidden Zones (4):**
Hidden (neutral), Hidden1 (red — contains HQ and EWR), Hidden2 (neutral), Hidden3 (neutral)

**Total: 61 zones** (all start RED except Batumi which starts BLUE, and hidden zones which start neutral)

---

## 29. Appendix — Full Config Reference

### All Config Settings Summary [VERIFIED against Foothold Config.lua]

| Setting | Type | Default | Section |
|---|---|---|---|
| `GlobalSettings.difficultyScaling` | Table | `{[1]=1.0, [2]=1.0}` | Difficulty |
| `GlobalSettings.supplyDifficultyScaling` | Table | `{[1]=1.0, [2]=1.0}` | Difficulty |
| `CapDifficulty` | String | `"medium"` | Difficulty |
| `CasSeadDifficulty` | String | `"medium"` | Difficulty |
| `FriendlyCapSupport` | String | `"medium"` | Difficulty |
| `FriendlyCasSupport` | String | `"medium"` | Difficulty |
| `FriendlySeadSupport` | String | `"medium"` | Difficulty |
| `AiPlaneSkill` | String | `"Random"` | Difficulty |
| `AiGroundSkill` | String | `"Excellent"` | Difficulty |
| `HideSAMOnMFD` | Bool/String | `true` | Difficulty |
| `RedReactiveConfig` | Table | (3 profiles) | Reactive |
| `UseStatics` | Boolean | `true` | Rules |
| `PVE_Only` | Boolean | `false` | Rules |
| `Era` | String | `"Modern"` | Rules |
| `NoSA10AndSA11` | Boolean | `false` | Rules |
| `NoTorM2AndPantsir` | Boolean | `false` | Rules |
| `NoSA15` | Boolean | `false` | Rules |
| `AllowMods` | Boolean | `false` | Rules |
| `CreditLosewhenKilled` | Boolean | `false` | Rules |
| `CreditLosewhenKilledAmount` | Number | `100` | Rules |
| `RankLoseWhenKilled` | Boolean | `true` | Rules |
| `RankLoseWhenKilledAmount` | Number | `100` | Rules |
| `SplashDamage` | Boolean | `false` | Rules |
| `ShowKills` | Boolean | `false` | Rules |
| `StoreLimit` | Boolean | `false` | Rules |
| `RankingSystem` | Boolean | `true` | Rules |
| `FriendlyFireRankPenalty` | Number | `500` | Rules |
| `InvisibleA10` | Boolean | `false` | Rules |
| `EscortTakeoffFromGround` | Boolean | `true` | Rules |
| `UseC130LoadAndUnload` | Boolean | `true` | Rules |
| `WarehouseLogistics` | Boolean | `true` | Logistics |
| `AIDeliveryamount` | Number | `20` | Logistics |
| `StrictSmartWeaponsInventory` | Boolean | `false` | Logistics |
| `AutoFillResources` | Number | `5` | Logistics |
| `NoAIBlueSupplies` | Boolean | `false` | Logistics |
| `RewardContribution` | Table | (see section 6) | Shop |
| `ShopPrices` | Table | (see section 9) | Shop |
| `ShopRankRequirements` | Table | (see section 9) | Shop |
| `ShopCategoryLabels` | Table | (see section 9) | Shop |
| `AIAttackTakeoffFromGround` | Boolean | `true` | Shop |
| `AIAttackTakeoffFromGroundExtraNM` | Number | `40` | Shop |
| `AllowScriptedSupplies` | Boolean | `false` | Shop |
| `RewardFlightTime` | Boolean | `true` | FlightTime |
| `FlightTimeRewardPerMinute` | Number | `2` | FlightTime |
| `RewardAllAircraft` | Boolean | `false` | FlightTime |
| `AllowedFlightTimeReward` | Table | (per-airframe) | FlightTime |
| `CTLDCost` | Boolean | `true` | CTLD |
| `CaptureZoneWithEngineer` | Boolean | `false` | CTLD |
| `CTLDUnitCapabilities` | Table | (see section 14) | CTLD |
| `CTLDPrices` | Table | (see section 14) | CTLD |
| `MAX_AT_SPAWN` | Table | (see section 5) | CTLD |
| `MAX_SAVED_FARPS` | Number | `3` | CTLD |
| `IRIS_RESTORE_UNIT_HEALTH_ON_MERGE` | Boolean | `false` | CTLD |
| `AllowedCsar` | Table | (see section 15) | CSAR |
| `PilotWeight` | Number | `80` | CSAR |
| `CsarHoverDistance` | Number | `20` | CSAR |
| `CsarHoverHeight` | Number | `60` | CSAR |
| `CsarHoverSeconds` | Number | `10` | CSAR |
| `CsarHostileInfantryChance` | Number | `25` | CSAR |
| `CapCountIgnoreTypes` | Table | (see section 12) | Advanced |
| `BlueCasCountIgnoreTypes` | Table | (see section 12) | Advanced |
| `RedCasCountIgnoreTypes` | Table | (see section 12) | Advanced |
| `TexacoSpeed` | Number | `286` | Tankers |
| `ArcoSpeed` | Number | `286` | Tankers |
| `CapLimitStages` | Table | (see section 12) | Scaling |
| `RedCasLimitStages` | Table | (see section 12) | Scaling |
| `BlueCapSupportStages` | Table | (see section 12) | Scaling |
| `BlueCasSupportStages` | Table | (see section 12) | Scaling |
| `BlueSeadSupportStages` | Table | (see section 12) | Scaling |
| `ewrs_*` | Various | (see section 21) | EWRS |
| `AIEN.config.*` | Various | (see section 11) | AIEN |
| `ForbiddWeaponsInAllEra` | Table | (nukes disabled) | Weapons |
| `restrictedWeapons` | Table | (Cold War list) | Weapons |
| `allowedPlanes` | Table | (Cold War allowed) | Weapons |
| `restockAircraft` | Table | (mod restock list) | Weapons |
| `WarehouseWeaponCaps` | Table | (smart weapon list) | Weapons |

---

*End of Foothold Extended Caucasus Research Document v2*
*All values verified against source files as of 2026-03-21*
