# Foothold Extended

A multiplayer PvE sandbox campaign for [DCS World](https://www.digitalcombatsimulator.com/). Fight your way across the map zone by zone, capturing airfields, destroying infrastructure, and pushing the frontline forward — all in a persistent, cooperative environment.

Foothold Extended supports **8 theaters** and **multiple eras**, so whether you prefer Cold War iron or modern precision, there is a battlefield waiting for you.

---

## Quick Install

Open **PowerShell** and paste this single line:

```
powershell -c "irm https://bojotex.github.io/Foothold-Extended/install.ps1 | iex"
```

The installer will:

1. Check that Python is available (and install it for you if not)
2. Detect your DCS Saved Games folder automatically
3. Let you pick which theater(s) to install
4. Ask which era you want to play (Modern, Cold War, or Gulf War)
5. Download and configure everything — ready to fly

That is all you need to do. No manual file copying, no unzipping, no editing.

---

## Theaters

| Theater | Map Required | Available Eras |
|---------|-------------|----------------|
| Caucasus | Caucasus (free) | Modern, Cold War |
| Syria | Syria | Modern, Cold War |
| Germany | Germany Cold War | Cold War |
| Iraq | Iraq (Persian Gulf '91) | Modern, Gulf War |
| Kola | Kola | Modern, Cold War |
| Persian Gulf | Persian Gulf | Modern, Cold War |
| Sinai Extended | Sinai | Modern, Cold War |
| Sinai North | Sinai | Modern, Cold War |

You only need the DCS terrain module for the theater you want to play. Caucasus is included free with DCS World.

---

## What is Foothold?

Foothold is a **cooperative PvE campaign** where all human players fight together on the blue coalition against AI-controlled red forces. The campaign is structured as a chain of zones across the map. You start at your home base and must capture zones in sequence by:

- **Suppressing enemy air defenses** (SEAD/DEAD) to clear the way
- **Striking enemy positions** to weaken zone defenders
- **Deploying ground troops** via helicopter or transport to capture the zone
- **Advancing the frontline** to unlock the next set of objectives

Progress is **persistent** — when zones change hands, the state is saved. The campaign continues across server restarts until the map is won (or lost).

### Key Features

- **All player aircraft are welcome.** Fly anything from an A-10 to an F-18 to a Huey. Every role matters.
- **CTLD logistics.** Airlift troops, deploy FOBs, and resupply the front via the CTLD system.
- **Dynamic briefings.** A built-in kneeboard generator creates a tactical FRAG-O briefing showing your current objectives, threats, and frontline status.
- **Multiple eras.** Choose between modern and Cold War loadouts (or Gulf War on the Iraq map). The era setting restricts available weapons and changes the enemy threat composition.
- **SRS integration.** SimpleRadio Standalone is supported for realistic communications.

---

## Kneeboard Briefings

Foothold Extended includes `briefing.pyw`, a small Python tool that generates a military-style kneeboard briefing card. It reads the current campaign state and produces a tactical summary showing:

- Situation overview (zones held, enemy strength)
- Mission objectives (what to attack, what to suppress)
- SEAD targets with threat system details
- Sustainment and support information

To generate a briefing, double-click `briefing.pyw` in your mission folder. The kneeboard image is placed where DCS can find it automatically — no server restart required.

---

## Manual Install

If you prefer to install manually instead of using the one-liner:

1. Go to the [Releases](https://github.com/BojoteX/Foothold-Extended/releases/latest) page
2. Download the `.miz` file for your theater and `briefing.pyw`
3. Create a folder in your DCS Saved Games directory:
   ```
   Saved Games\DCS\Missions\Foothold Extended - Caucasus\
   ```
4. Place both files in that folder
5. In DCS, load the `.miz` from the Mission Editor or Multiplayer Host screen

To change the era, open the `.miz` (it is a ZIP file), find `l10n/DEFAULT/Foothold Config.lua`, and change the `Era` setting to `"Modern"`, `"Coldwar"`, or `"Gulfwar"`.

---

## Updating

Run the same install command again:

```
powershell -c "irm https://bojotex.github.io/Foothold-Extended/install.ps1 | iex"
```

The installer will detect your existing installation, show whether an update is available, and replace the files cleanly. Each update is a fresh install — you will be asked to choose your era again.

Campaign save files are **not** affected by updates. Your progress is preserved.

---

## Requirements

- [DCS World](https://www.digitalcombatsimulator.com/) (standalone or Steam)
- The terrain module for your chosen theater (Caucasus is free)
- Windows 10 or 11
- Python 3.10 or newer (the installer will set this up for you if needed)

---

## Credits

**Mission design:** Lekaa

Foothold Extended is a community project. Contributions, bug reports, and feedback are welcome via [GitHub Issues](https://github.com/BojoteX/Foothold-Extended/issues).

---

## License

This project is provided as-is for the DCS community. The mission files are based on Lekaa's Foothold framework.
