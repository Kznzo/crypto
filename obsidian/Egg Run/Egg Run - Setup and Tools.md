---
tags: [egg-run, setup, claude]
updated: 2026-11-27
---
# Egg Run: setup and tools

Back to [[Egg Run - Start Here]]

## Where things are

| What | Where |
|---|---|
| Project (git repo `Kznzo/crypto`) | `~/crypto`, branch **`claude/gracious-goodall-6624rv`** |
| Game code | `~/crypto/games/egg-run/` (see its README) |
| These notes | `~/crypto/obsidian/Egg Run/` (linked into the vault) |
| Full setup guide | `~/crypto/BLENDER-ROBLOX.md` |
| LihFolk vault (Obsidian) | `~/LihFolk Vault V2` |
| LihFolk asset pack | `~/LihFolk-Assets` |
| My private skills | `~/.claude/skills/` (**never put them in the repo**: it's public and the licenses forbid sharing) |

## Claude Code agents

| Agent | Does |
|---|---|
| **blender** | Works live in Blender 5.1+ through the official Blender Lab MCP server. Uses blender-skills, LihFolk `roblox-blender-modeling`, and my `lihfolk-stud-voxel` and `folk-treadmills` skills |
| **roblox** | Works live in Roblox Studio through Studio's built-in MCP server. Uses the LihFolk skills and vault, `folk-stud-ui` for menus, and the LihFolk code checker |

Both run without permission prompts (`.claude/settings.json`).

## Plugins and skills

- **blender-skills** (ra100): 8 Blender 5.x API guides
- **LihFolk** (lihfolk-cy/v2-vault): 22 Roblox skills, 1,300+ notes, a Luau code checker hook, ready-made systems
- **Private skills** (in `~/.claude/skills`):
  - **folk-stud-ui**: stud-style Roblox menus (HUD, shop, egg shop, quests, backpack, index, settings, rebirth)
  - **lihfolk-stud-voxel**: stud/LEGO voxel models (pets with rigs, mobs, bosses, buildings, props, terrain)
  - **folk-treadmills**: voxel treadmills with rarities, animations and VFX (proprietary)
- Install the private skills on a new computer:
  `mkdir -p ~/.claude/skills && cd ~/Downloads && unzip -o folk-stud-ui.skill -d ~/.claude/skills && unzip -o Folk_Stud-Voxel_Model_Skill.zip -d ~/.claude/skills && unzip -o treadmill_SKILL_ONLY.zip -d ~/.claude/skills`

## Commands (type in Claude Code)

| Command | Does |
|---|---|
| `/build-map` | Builds the Egg Run map in Studio, takes screenshots and playtests |
| `/test-blender` | Safe Blender smoke test |
| `/test-roblox` | Safe Roblox Studio smoke test |
| `/test-pipeline` | Imports a Blender asset into Studio and scripts it (treasure chest example) |
| `/lihfolk:audit` | Checks game scripts for exploits and bugs |
| `/lihfolk:assets <what>` | Finds an asset in the LihFolk asset pack |
| `/lihfolk:new-system` | Installs a ready-made LihFolk system |
| `/mcp` | Shows whether Blender and Roblox_Studio are connected |

## One-time setup (already done on my Mac)

Run `cd ~/crypto && bash setup-claude-agents.sh`. It installs uv and git, the Blender MCP server and add-on, both plugins and the LihFolk vault and assets, and connects Roblox Studio. Then in Studio: Assistant → … → Manage MCP Servers → **Enable Studio as MCP server**.
