# Claude + Blender + Roblox Studio

This folder sets Claude Code up to work live in **Blender** and **Roblox Studio** on your computer. Claude can see your scene or place, build and edit things, write scripts, and playtest.

| File | What it does |
|---|---|
| `.mcp.json` | Connects Claude Code to Blender when it's opened in this folder |
| `.claude/agents/blender.md` | The **blender** agent, a Blender specialist (modelling, materials, animation, export for Roblox) |
| `.claude/agents/roblox.md` | The **roblox** agent, a Roblox Studio specialist (building, Luau, UI, playtesting, assets) |

> **Run Claude Code on your own computer.** Blender and Roblox Studio are desktop apps, so Claude has to run on the same machine to reach them. A cloud session on claude.ai can't. Use the **Claude desktop app → Code** tab and pick this folder, or run `claude` in a terminal inside this folder.

---

## One-time setup

### 1. Get these files on your computer

In this project's folder:

```bash
git fetch origin claude/gracious-goodall-6624rv
git checkout claude/gracious-goodall-6624rv
```

(Or merge that branch into your main branch.)

### 2. Blender

1. **Install uv**, which runs the Blender connector:
   - macOS: `brew install uv`, or `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows: `winget install --id=astral-sh.uv -e`

   Then open a **new** terminal.
2. **Install the Blender add-on:**
   ```bash
   uvx mcp-for-blender install-addon
   ```
3. In Blender, go to **Edit → Preferences → Add-ons** and enable **MCP for Blender**.
4. In the 3D Viewport, press **N**, open the **MCP for Blender** tab, and click **Connect to Claude** if you see that button.

You don't need to change any Claude config: `.mcp.json` already adds the `blender` server for this folder. Anonymous telemetry is turned off there (`DISABLE_TELEMETRY`).

*Want Blender in Claude Desktop or other apps too? Run `uvx mcp-for-blender setup` and pick them.*

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

Open Blender (add-on connected) and Roblox Studio (a place open). Then start Claude Code in this folder:

1. When Claude Code asks whether to use the `blender` server from `.mcp.json`, approve it.
2. Type `/mcp`. Both **blender** and **Roblox_Studio** should show as connected.
3. Type `/agents`. You should see **blender** and **roblox**.

---

## Using it

Ask in plain language. Claude hands Blender work to the blender agent and Studio work to the roblox agent. You can also name the agent yourself:

- "Use the blender agent to model a low-poly treasure chest with a lid that opens, then export it for Roblox."
- "Look at my Blender scene and add three-point lighting and a camera for a product shot."
- "Use the roblox agent to make a checkpoint system with a leaderboard of stages reached, then playtest it."
- "Find out why my sword doesn't do damage and fix it."

**From Blender to Roblox:**
1. The blender agent builds the model, keeps it within Roblox's limits, bakes the textures, and exports it to a `roblox_exports/` folder next to your .blend file.
2. You import that file in Roblox Studio with **Import 3D** (the 3D Importer), with the scale unit set to meters.
3. The roblox agent places it, sets collisions and materials, and scripts it.

Both tools ask for permission before they act. Choose "always allow" for the ones you trust.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `blender` shows *failed* in `/mcp`, or you see `spawn uvx ENOENT` | The app can't find `uvx`. Get its full path with `which uvx` (macOS) or `where uvx` (Windows), and replace `"uvx"` in `.mcp.json` with that path. |
| Blender tools say *connection refused* | Blender must be open with the add-on connected (N panel → MCP for Blender). Don't run `uvx mcp-for-blender` yourself, because Claude starts it. The first command sometimes fails, so try again. |
| No Roblox tools in `/mcp` | Check that **Enable Studio as MCP server** is on, then restart Studio **and** Claude Code. On Windows, also quit Claude from the system tray. |
| Roblox says it can't save | Save the place once yourself (File → Save to Roblox or Save to File). After that, Claude can save it. |
| Several Studio windows are open | That's fine. The roblox agent asks which place to work in. |

## Safety

Both connections let Claude **run code inside the apps** (Python in Blender, Luau in Studio), which can change or delete your work.
- Save before big changes. The blender agent saves a `.checkpoint.blend` copy first, and the roblox agent never publishes.
- Only use these connections with projects you're okay with Claude changing.
