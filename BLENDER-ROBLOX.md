# Claude + Blender + Roblox Studio

This folder sets Claude Code up to work live in **Blender** and **Roblox Studio** on your computer. Claude can see your scene or place, build and edit things, write scripts, and playtest.

| File | What it does |
|---|---|
| `.mcp.json` | Connects Claude Code to Blender through the **official Blender Lab MCP server** |
| `.claude/settings.json` | Installs the [blender-skills plugin](https://github.com/ra100/blender-claude-plugin), switches on the Blender server, and lets Claude use every Blender and Roblox Studio tool without asking you each time |
| `.claude/agents/blender.md` | The **blender** agent, a Blender specialist (modelling, nodes, materials, rigging, physics, rendering, export for Roblox) |
| `.claude/agents/roblox.md` | The **roblox** agent, a Roblox Studio specialist (building, Luau, UI, playtesting, assets) |
| `.claude/commands/test-blender.md`, `test-roblox.md`, `test-pipeline.md` | The `/test-blender`, `/test-roblox` and `/test-pipeline` tests |
| `examples/treasure-chest/` | A Roblox-ready treasure chest the blender agent made during testing (FBX + baked textures + preview) |
| `Setup-Claude-Agents.bat` (Windows), `Setup-Claude-Agents.command` (Mac) | Double-click, one-time setup: installs uv, git and the plugin, downloads the Blender server, connects Roblox Studio |

> **Run Claude Code on your own computer.** Blender and Roblox Studio are desktop apps, so Claude has to run on the same machine to reach them. A cloud session on claude.ai can't. Use the **Claude desktop app → Code** tab and pick this folder, or run `claude` in a terminal inside this folder.

---

## Quick start (about 10 minutes)

1. **Get the files:** in this project's folder, run `git fetch origin claude/gracious-goodall-6624rv` and then `git checkout claude/gracious-goodall-6624rv`.
2. **Double-click the setup script:** `Setup-Claude-Agents.bat` on Windows, or `Setup-Claude-Agents.command` on Mac. If it installs uv or git, it asks you to run it once more.
3. **Blender 5.1+:** install the **MCP** add-on and allow online access (step 2 below).
4. **Roblox Studio:** turn on **Enable Studio as MCP server** (step 3 below). The setup script connects it to Claude Code. Run the script again if you turned this on afterwards.
5. **Open Blender and Roblox Studio** with a place open, then open Claude Code in this folder. Say **yes** to "trust this folder" and accept the **blender-skills** plugin if it's offered.
6. **Test:** type `/test-blender`, then `/test-roblox`. Each one does a safe test: it builds only inside a `Claude_Test` collection or folder, checks the result, and gives you a ✅/❌ checklist.
7. **Test the whole pipeline:**
   - In Studio, use **Import 3D** to import `examples/treasure-chest/TreasureChest.fbx` with the scale unit set to **Meter**.
   - Type `/test-pipeline`. The roblox agent turns it into a chest whose lid opens with **E**, and playtests it.
   - The roblox test commands don't save your place, so you can close it without saving to undo everything.

If something fails, the detailed steps and troubleshooting are below.

---

## One-time setup (detailed)

### 1. Get these files on your computer

In this project's folder:

```bash
git fetch origin claude/gracious-goodall-6624rv
git checkout claude/gracious-goodall-6624rv
```

(Or merge that branch into your main branch.)

### 2. Blender (version 5.1 or newer)

1. **Install the MCP add-on** from Blender Lab. Either:
   - **Drag and drop:** open [this link](https://projects.blender.org/lab/blender_mcp/releases/download/v1.0.0/mcp-1.0.0.zip?repository=https%3A%2F%2Flab.blender.org%2F&blender_version_min=5.1.0) in your browser and drag it into Blender twice. The first time adds the Blender Lab repository; the second installs the add-on.
   - **From a file:** download [mcp-1.0.0.zip](https://projects.blender.org/lab/blender_mcp/releases/download/v1.0.0/mcp-1.0.0.zip), then in Blender go to **Edit → Preferences → Get Extensions → Install from Disk…** and pick the zip.
2. Allow online access, which the add-on needs: **Edit → Preferences → System → Network → Allow Online Access**.
3. Under **Edit → Preferences → Add-ons → MCP**, check that the add-on is enabled and its server is running on port 9876. It starts automatically.
4. **Install uv** and **git** if you don't have them. Claude uses them to start the Blender server.
   - uv on macOS: `brew install uv`, or `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - uv on Windows: `winget install --id=astral-sh.uv -e`
   - git on Windows: `winget install --id Git.Git -e`

   Then open a **new** terminal.

You don't need to change any Claude config: `.mcp.json` already starts the official server for this folder.

> **On an older Blender (before 5.1)?** The official add-on won't install. Use the community server instead:
> 1. Run `uvx mcp-for-blender install-addon` and enable **MCP for Blender** in Blender.
> 2. In `.mcp.json`, replace the `"args"` list with `["mcp-for-blender"]`.
>
> Both add-ons use port 9876, so only enable one of them. The blender agent works with either.

### 3. Roblox Studio

Roblox Studio has its own MCP server built in.

1. In Studio, open **Assistant → … → Manage MCP Servers** and turn on **Enable Studio as MCP server**.
2. In the same panel, under **Quick connect**, turn on **Claude Code**.
3. Restart Roblox Studio and Claude Code.

If Quick connect doesn't work, add the server yourself with one command:

- **macOS**
  ```bash
  claude mcp add --scope user Roblox_Studio -- /Applications/RobloxStudio.app/Contents/MacOS/StudioMCP
  ```
- **Windows**
  ```bash
  claude mcp add --scope user Roblox_Studio -- cmd.exe /c %LOCALAPPDATA%\Roblox\mcp.bat
  ```

If you installed the older `studio-rust-mcp-server` plugin earlier, disable it so Claude doesn't get two sets of Roblox tools.

### 4. Check that everything is connected

Open Blender (with the MCP add-on running) and Roblox Studio (with a place open). Then start Claude Code in this folder:

1. When Claude Code asks whether you trust this folder, say **yes**. You only do this once. It turns on the settings in `.claude/settings.json`: the `blender` server starts automatically, and the agents stop asking before each action.
2. When Claude Code offers to install the **blender-claude-marketplace** and the **blender-skills** plugin, accept. If it doesn't offer, run these two commands:
   ```bash
   claude plugin marketplace add ra100/blender-claude-plugin
   claude plugin install blender-skills@blender-claude-marketplace
   ```
3. Type `/mcp`. Both **blender** and **Roblox_Studio** should show as connected.
4. Type `/agents`. You should see **blender** and **roblox**.

---

## Using it

Ask in plain language. Claude hands Blender work to the blender agent and Studio work to the roblox agent. You can also name the agent yourself:

- "Use the blender agent to model a low-poly treasure chest with a lid that opens, then export it for Roblox."
- "Make a geometry-nodes rock scatter on the ground plane."
- "Look at my Blender scene and add three-point lighting and a camera for a product shot."
- "Use the roblox agent to make a checkpoint system with a leaderboard of stages reached, then playtest it."
- "Find out why my sword doesn't do damage and fix it."

The blender agent loads the right **blender-skills** guide for each job (geometry nodes, shaders, rigging, physics and so on). It also checks Blender's own bundled documentation, so it uses the correct API for your version.

**From Blender to Roblox:**
1. The blender agent builds the model, keeps it within Roblox's limits, bakes the textures, and exports it to a `roblox_exports/` folder next to your .blend file.
2. You import that file in Roblox Studio with **Import 3D** (the 3D Importer), with the scale unit set to meters.
3. The roblox agent places it, sets collisions and materials, and scripts it.

**No permission prompts:** `.claude/settings.json` pre-approves every Blender and Roblox Studio tool, so the agents just work. If Roblox actions still ask for permission, your Roblox server has a different name. Find its name in `/mcp`, then add `"mcp__<that name>"` to the `allow` list in that file.

---

## What has been tested

- **Blender side: tested for real.** It ran on Blender 5.2.5 LTS with the official MCP add-on and server.
  - The blender agent built, baked and exported the chest in `examples/treasure-chest/`, and re-imported the FBX to check sizes and pivots.
  - `/test-blender` passed all five checks.
  - The Blender in that test had no window, so the screenshot tools weren't exercised. They should work in your normal Blender.
- **The macOS/Linux setup script** ran successfully, including a second run.
- **Not tested yet:**
  - The roblox agent, `/test-roblox` and `/test-pipeline`, because Roblox Studio only runs on Windows and macOS.
  - The Windows setup script.

  Your first run of these is the real test. If something fails, paste the ✅/❌ checklist to Claude and ask it to fix the agent.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `blender` shows *failed* in `/mcp`, or you see `spawn uvx ENOENT` | The app can't find `uvx`. Get its full path with `which uvx` (macOS) or `where uvx` (Windows), and replace `"uvx"` in `.mcp.json` with that path. Also check that `git --version` works. |
| Blender tools say they can't connect | Blender 5.1+ must be open with the **MCP** add-on running (Preferences → Add-ons → MCP) and online access allowed. Check that no other add-on is using port 9876. |
| The add-on won't install | Your Blender is older than 5.1. Update Blender, or use the community server (see the note in step 2). |
| Blender skills aren't used | Check that the plugin is installed with `claude plugin list`. If it isn't, run the two commands from step 4. |
| No Roblox tools in `/mcp` | Check that **Enable Studio as MCP server** is on, then restart Studio **and** Claude Code. On Windows, also quit Claude from the system tray. |
| Roblox says it can't save | Save the place once yourself (File → Save to Roblox or Save to File). After that, Claude can save it. |
| Several Studio windows are open | That's fine. The roblox agent asks which place to work in. |
| Mac says `Setup-Claude-Agents.command` can't be opened | Right-click it, choose **Open**, then confirm. Or run `./setup-claude-agents.sh` in Terminal. |
| `/test-blender` or `/test-roblox` isn't found | Start Claude Code from this folder. The commands live in `.claude/commands/`. |

## Safety

Both connections let Claude **run code inside the apps** (Python in Blender, Luau in Studio), with no sandbox, so it can change or delete your work. Prompts are turned off, so Claude won't stop to ask first.
- Save before big changes. The blender agent saves a `.checkpoint.blend` copy first, and the roblox agent never publishes.
- Only use these connections with projects you're okay with Claude changing.
