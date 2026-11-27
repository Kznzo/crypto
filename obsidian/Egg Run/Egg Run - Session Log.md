---
tags: [egg-run, log]
updated: 2026-11-27
---
# Egg Run: session log

Back to [[Egg Run - Start Here]]

## Day 1 (26-27 Nov 2026)

**Setup**
- Created the Claude Code agents **blender** and **roblox**, connected to Blender (MCP) and Roblox Studio (built-in MCP), with no permission prompts.
- Added the **blender-skills** plugin and switched to the official Blender Lab MCP server.
- Tested the blender agent in a real Blender 5.2.5: it made a treasure chest (now in `examples/treasure-chest/`). Fixed its instructions from the test.
- Added the `/test-blender`, `/test-roblox` and `/test-pipeline` commands and the double-click setup scripts.
- Added **LihFolk Vault V2** (plugin, Obsidian vault, asset pack), checked for safety first. Its code checker caught all 6 bugs in a test script.
- Ran the setup on my Mac: everything ✅.

**Game**
- Picked the design: NPC arena, stamina + speed, auto-battle, cute real animals. See [[Egg Run - Game Design]].
- Balance checked with a Python simulation.
- Used the **Voxel Stud Egg Pack** (9 eggs → 9 zones). Didn't use the Spin a Card or Steal a Brainrot files (see [[Egg Run - Decisions]]).
- Map redesigned to match my reference screenshot (wide checker canyon). Made a **voxel kit** in Blender (20 pieces). Wrote **MapBuilder** and the `/build-map` command. See [[Egg Run - Map]].
- Added my private skills: **folk-stud-ui**, **lihfolk-stud-voxel** and **folk-treadmills**. Both agents know when to use them.

**Next:** see [[Egg Run - Next Steps]].
