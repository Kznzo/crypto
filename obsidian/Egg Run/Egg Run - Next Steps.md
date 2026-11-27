---
tags: [egg-run, todo]
updated: 2026-11-27
---
# Egg Run: next steps

Back to [[Egg Run - Start Here]]

## 1. Map (now)
- [ ] `git pull`, then `/build-map` in Studio, and look at the screenshots and the playtest
- [ ] Optional: import `EggRunKit.glb` into ReplicatedStorage as `EggRunKit`, paste `EggPack` into ReplicatedStorage, and rebuild
- [ ] Write down what to change (colours, width, props, landmarks), then ask Claude to adjust the map
- [ ] Optional upgrade: stud-textured props from **lihfolk-stud-voxel** (see [[Egg Run - Map]])

## 2. Gameplay systems (server)
Built on the LihFolk modules already in `games/egg-run/src` (PlayerData saving, Currency, Net remotes, Odds):
- [ ] **Plots**: assign a base on join, owner sign, spawn at base
- [ ] **Run**: start at the start line, server-side distance (anti-teleport), stamina countdown, egg of the furthest zone, back to base
- [ ] **Pets**: hatch (odds from Config), inventory of 60, team of 3, equip/unequip/release, levels and XP
- [ ] **Training**: XP per second while standing on your training pad
- [ ] **Upgrades**: Speed, Stamina, Training (coins)
- [ ] **Arena**: battle simulation on the server, rewards, best level
- [ ] **Main** script that wires everything together, then save and load test

## 3. Client and UI
- [ ] Menus in the **folk-stud-ui** style: HUD (coins, best zone), stamina bar during a run, animals backpack and index, upgrades shop, arena panel, egg odds
- [ ] Hatch reveal with the voxel egg cracking open
- [ ] Animals following the player (team of 3)
- [ ] Arena battle playback (camera on the Battle Box)

## 4. Art
- [ ] The 24 animals as stud voxel pets with **lihfolk-stud-voxel** (box rig + walk and idle clips): start with Puppy, Kitten, Bunny, Chick
- [ ] Treadmills for the bases with **folk-treadmills** (training)
- [ ] Sky and lighting pass (the egg pack has a sky)

## 5. Later
- [ ] Rebirth, daily rewards, codes, leaderboards (LihFolk systems)
- [ ] Monetization only with the rules in mind (show odds, no paid random items for restricted accounts)
- [ ] Test on a phone (performance budget)
