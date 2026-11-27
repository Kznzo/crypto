---
tags: [egg-run, decisions]
updated: 2026-11-27
---
# Egg Run: decisions and why

Back to [[Egg Run - Start Here]]

| Decision | Why |
|---|---|
| **Didn't use** the "Spin a Card" and "Steal a Brainrot" map files | Spin a Card is a copy of someone else's published game (65 of its 92 scripts are decompiled code), and the Steal a Brainrot maps are that game's own map. Using them risks a takedown, so the map is our own design in the same genre. |
| **Used** the Voxel Stud Egg Pack | Clean (no scripts). Its 9 eggs became the 9 zones. |
| Corridor = **wide canyon** (140 studs, checker walls) | Matches my reference screenshot |
| **1 Blender unit = 1 stud** for Roblox models | LihFolk convention. Import with Scale Unit **Studs**. (The old treasure chest example is in meters: import it with **Meter**.) |
| Kit export: **one vertex-colour set (COLOR_0)** | Bug found in a Blender test render: the first export put white in COLOR_0, so Roblox would have shown every prop white. Fixed. |
| Official **Blender Lab MCP** server (needs Blender 5.1+) | The blender-skills plugin is built for it, and it includes Blender's own API docs |
| Private skills stay in `~/.claude/skills`, **not in the repo** | The repo is public, and folk-treadmills' license forbids sharing |
| Eggs are **earned by running**, never sold for Robux (for now) | Keeps clear of paid-random-item rules. Odds are shown anyway. |
| Server decides everything (distance, odds, fights, coins) | Stops exploits. Uses LihFolk's Net (validated remotes) and PlayerData (safe saving). |
