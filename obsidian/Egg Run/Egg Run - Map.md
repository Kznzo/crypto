---
tags: [egg-run, map, worldbuilding]
updated: 2026-11-27
---
# Egg Run: map

Back to [[Egg Run - Start Here]]

**Style target:** my reference screenshot, a **wide canyon** with tall **checkerboard walls** topped with grass, a bright **checkered floor**, **blocky voxel props** along the walls, and big landmarks in the distance. The map is original: no copied maps from other games. Built with the LihFolk worldbuilding method: layout → primary forms → medium props → detail.

## Layout ("Hatch Plaza" + the canyon)

| Area | Details |
|---|---|
| **Hub** | Grass plaza with a stud-grid overlay; a cream aisle lined with voxel lamp posts; the spawn faces the canyon; "RUN FOR EGGS" and "BATTLE BOX" signposts |
| **Bases** | 6 plots (3 each side of the aisle), each a different colour: mint, sky, peach, lilac, lemon, coral. Each has a low voxel wall, an **owner sign**, a glowing **TRAINING PAD**, 3 **podiums** for the team, trees and flowers |
| **Battle Box** | Behind the plaza: checkered floor, glass walls, blue (mine) and red (enemy) team pads, a viewing deck with a ramp, a big sign, 2 lights |
| **Start** | "RUN FOR EGGS!" banner across the canyon mouth with a **giant Golden Egg** on top (the landmark seen from everywhere), and a white start line |
| **Canyon** | 140 studs wide, 80-stud checker walls (20-stud squares), coloured cap strip, centre ±42 kept clear for running |
| **End** | Golden end wall, "YOU MADE IT TO THE END!" and a big Golden Egg on a pedestal |

## The 9 zones

| # | Zone | Walls | Floor | Landmark | Props |
|---|---|---|---|---|---|
| 1 | Meadow | terracotta | green grass | giant tree | bushes, flowers, trees |
| 2 | Farm | tan | light green | red barn | hay, bushes, trees |
| 3 | Hive | honey | yellow sand | beehive | flowers, bushes |
| 4 | Beach | sky blue | sand | **rainbow arch over the run** | palms, rocks |
| 5 | Snow | ice blue | snow | snowman | pines, ice, rocks |
| 6 | Volcano | dark red-brown | basalt | volcano + lava pools | lava rocks |
| 7 | Storm | slate purple | slate | big storm cloud | rocks, pines, clouds |
| 8 | Crystal | lavender | lilac | giant crystal | purple and cyan crystals |
| 9 | Golden | gold | cream | golden pyramid | gold pillars, gold crystals |

Each zone has a **banner** ("ZONE 2 FARM"), a glowing line on the floor, the zone's **egg floating** above the run with a label ("Bee Egg / up to Epic"), and **distance markers** every 100 studs.

## The voxel kit (made in Blender)

`games/egg-run/assets/EggRunKit.glb` holds 20 pieces, all passing LihFolk's quality checks. They use vertex colours and 1 unit = 1 stud.
- **Props:** VBush, VBushSmall, VCactus, VRock, VTree, VPalm, VPine, VHay, VFlower, VIce, VLavaRock, VCloud, VCrystal, VPillar
- **Landmarks:** LBarn, LBeehive, LRainbow, LSnowman, LVolcano, LPyramid
- **Tintable:** VRock, VIce and VCrystal are painted near-white so the map can colour them per zone.
- **Rebuild it:** `tools/voxel_kit.py` (run with Blender).

![[egg-run-kit-preview.png]]

## Build / rebuild in Studio

- In Claude Code (`~/crypto`), type **`/build-map`**: it creates the scripts, builds the map, sets WalkSpeed 60 for the preview, takes screenshots and playtests.
- Or from Studio's command bar: `require(game.ServerScriptService.EggRun.MapBuilder).Build()`
- **Optional, for the full look:**
  - **Kit:** Import 3D `EggRunKit.glb` with Scale Unit **Studs**, move it into ReplicatedStorage, and name it **EggRunKit**.
  - **Egg pack:** copy `Workspace.EggPack` from `Voxel_Stud_Egg_Pack.rbxl` into ReplicatedStorage.
  - Without these, the map builds from blocks in the same style.

## Ideas to try after the first look

- [ ] Rebuild the map props with **lihfolk-stud-voxel** (props_brick: Oak, Pine, Bush, Rocks, Lamp, Fence; terrain_brick: Cliff, Waterfall) for real **stud textures**, like the reference.
- [ ] Put a stud texture on the walls and floor (upload `roblox_square_studs.png` once, then set its ID in MapBuilder).
- [ ] Replace each base's training pad with a **treadmill** (folk-treadmills).
