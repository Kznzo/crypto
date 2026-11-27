---
description: Smoke-test the roblox agent in your open Roblox Studio place (safe, touches only a Claude_Test folder, doesn't save)
---

Use the **roblox** agent to run this smoke test in my open Roblox Studio place. Give it these instructions:

1. **Connection:** call `list_roblox_studios` and report the open place names. If there's more than one, pick the first and say which one you picked. Call `get_studio_state` and make sure Studio is in Edit mode, not playing. If the tools are missing or can't connect, stop and give me the troubleshooting steps from your instructions.
2. **Explore:** with `search_game_tree`, summarise the place in a few lines: the main folders, and roughly how many Scripts, LocalScripts and ModuleScripts it has.
3. **Build:** in Workspace, create a Folder named `Claude_Test`. Inside it **only**:
   - Add an anchored, neon, 6×1×6 Part named `TestPad`, placed next to the SpawnLocation (or at 0, 1, 10 if there is none).
   - Add a server Script named `TestPadScript` that does two things. When the script starts, it prints `Claude test: server script running`. When a player's character touches the pad, it turns the pad green and prints `Claude test: pad touched by <player name>`. Use a debounce, `game:GetService` and `task.wait`.
   Don't change anything outside `Claude_Test`.
4. **Playtest:** start a playtest with `start_stop_play`. Walk the character onto `TestPad` with `character_navigation`. Read `get_console_output` and take a `screen_capture`. Then stop the playtest.
5. **Check:** confirm both messages appeared in the output and that there were no new errors from `TestPadScript`.

**Don't save the place.** That way I can throw the test away by closing without saving.

Then report a checklist to me: ✅ or ❌ for connection, explore, build, playtest and check, with a one-line note for each. End by telling me I can say "delete the Claude_Test folder" to remove the test, or close the place without saving.
