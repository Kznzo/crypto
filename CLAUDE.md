# CLAUDE.md

This repo holds two projects:
- **ClipForge** (French clip-making app: `clipforge/`, `Lancer-ClipForge.*`). Leave it alone unless asked.
- **Egg Run**, a Roblox game in progress: `games/egg-run/`.

## Egg Run: read these first

Notes (also linked into the user's Obsidian vault): `obsidian/Egg Run/`
- `Egg Run - Start Here.md`: status and how to resume
- `Egg Run - Next Steps.md`: the to-do list (continue with the first unchecked item)
- `Egg Run - Game Design.md`, `Egg Run - Map.md`, `Egg Run - Decisions.md`, `Egg Run - Setup and Tools.md`

When you finish a piece of work, update `Next Steps` (tick it off) and add a line to `Egg Run - Session Log.md`.

## How to work here

- **Agents:** use the **roblox** agent for Roblox Studio (built-in Studio MCP) and the **blender** agent for Blender (Blender Lab MCP).
- **Map:** `/build-map` builds it in Studio. The source of truth is the code in `games/egg-run/src` (`Config.luau` holds every number).
- **Skills:**
  - LihFolk plugin skills (`lihfolk:*`) for Roblox systems and knowledge
  - blender-skills for the Blender API
  - the private skills `folk-stud-ui` (menus), `lihfolk-stud-voxel` (stud voxel pets and props) and `folk-treadmills` (treadmills)
- **Never copy the private skills** (`~/.claude/skills`) into this repo. It's public, and their licenses forbid sharing.
- **Never build on other games' maps or code.** We rejected the "Spin a Card" and "Steal a Brainrot" files. Keep the game original.
- **Roblox models:** 1 Blender unit = 1 stud; import with Scale Unit **Studs**. Export exactly one vertex-colour set (COLOR_0).
- **Server-authoritative gameplay** on the LihFolk modules in `games/egg-run/src/*/LihFolk` (PlayerData, Currency, Net, Odds). Credit them in `CREDITS.md`.
- **Branch:** `claude/gracious-goodall-6624rv`.
