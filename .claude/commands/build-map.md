---
description: Build the Egg Run map (canyon, bases, Battle Box) in your open Roblox Studio place for a first look and a test run
---

Use the **roblox** agent to build the Egg Run map in my open Roblox Studio place. Give it these steps:

1. **Connect:** call `list_roblox_studios` and pick the open place (if several, say which you picked). Make sure Studio is in Edit mode.
2. **Create the scripts from this repo.** Recreate each file below as an exact copy in Studio: same name and folder, and the file's full content as the Source. Use the script type shown. Create any missing folders.
   | Repo file | Studio location | Type |
   |---|---|---|
   | `games/egg-run/src/ReplicatedStorage/EggRun/Config.luau` | `ReplicatedStorage.EggRun.Config` | ModuleScript |
   | `games/egg-run/src/ReplicatedStorage/EggRun/Layout.luau` | `ReplicatedStorage.EggRun.Layout` | ModuleScript |
   | `games/egg-run/src/ReplicatedStorage/EggRun/Props.luau` | `ReplicatedStorage.EggRun.Props` | ModuleScript |
   | `games/egg-run/src/ServerScriptService/EggRun/MapBuilder.luau` | `ServerScriptService.EggRun.MapBuilder` | ModuleScript |

   If a ModuleScript can't be created with `multi_edit`, create it with `execute_luau` (`Instance.new("ModuleScript")`, set `Name`, set `Source` to the file text, then parent it).
3. **Optional assets:** check whether `ReplicatedStorage.EggRunKit` (the voxel kit imported from `games/egg-run/assets/EggRunKit.glb`) and `ReplicatedStorage.EggPack` (from the Voxel Stud Egg Pack place) exist. Tell me which are missing. The map still builds without them, from blocks in the same style.
4. **Build:** with `execute_luau` in the Edit datamodel, run `require(game.ServerScriptService.EggRun.MapBuilder).Build()`. Then report the part count under `Workspace.EggRunMap` and the `BuiltWithKit` and `BuiltWithEggPack` attributes.
5. **First-look settings:** set `StarterPlayer.CharacterWalkSpeed = 60` so the canyon is quick to run. The real game will control speed later. Tell me you set it.
6. **Look:** take screenshots with `screen_capture`:
   - from the spawn, looking at the START banner and the giant egg
   - from the start line, looking down the canyon
   - one overview from high above the hub
7. **Run test:**
   - Start a playtest. Walk the character from the spawn into the canyon and down it for about 15 seconds with `character_navigation`.
   - Take a `screen_capture` while running.
   - Read `get_console_output` for errors, then stop the playtest.
8. **Save:** call `save_place` only if the place has been saved before. Never publish.

Then report back:
- the screenshots
- any errors
- anything that looks wrong: floating props, props blocking the run, wrong colours, missing kit or egg pack
- the exact steps to import the kit or egg pack, if they're missing
