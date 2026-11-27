---
description: Blender → Roblox pipeline test - set up the imported treasure chest in Studio with an opening lid and playtest it (doesn't save)
---

I've imported a chest made in Blender into my open Roblox Studio place with the 3D Importer (scale unit: Meter). By default it's `examples/treasure-chest/TreasureChest.fbx` from this repo. If the blender agent just exported a different chest, it's that one. Details are in `examples/treasure-chest/README.md`.

Use the **roblox** agent to do the following, and pass it the hinge details from that README:

1. **Find it:** with `list_roblox_studios` and `search_game_tree`, find the imported model and its two MeshParts, `Chest_Base` and `Chest_Lid`. If they aren't there, stop and remind me to import the FBX with Import 3D first.
2. **Set it up:**
   - Put both parts in a Model named `TreasureChest` inside a Workspace folder named `Claude_Test`, with `Chest_Base` as the `PrimaryPart`.
   - Anchor both parts. Place the chest on the ground near the SpawnLocation.
   - Report its size in studs next to a 5-stud-tall character, so I can tell whether the scale looks right.
3. **Textures:** if the parts look untextured, add a `SurfaceAppearance` to each using the PNG maps in `examples/treasure-chest/`, as your instructions describe.
4. **Hinge:** set `Chest_Lid`'s `PivotOffset` to its back hinge edge, the edge that touches the back of `Chest_Base`.
5. **Script it:**
   - Add a `ProximityPrompt` to `Chest_Base` with ActionText "Open" and the E key.
   - Add a server Script that toggles the lid between closed and about 100° open around the hinge, using TweenService on a CFrameValue and `PivotTo`. Switch the ActionText between "Open" and "Close".
   - Use a debounce so it can't be spammed.
6. **Playtest:**
   - Start play and walk the character to the chest with `character_navigation`.
   - Press E with `user_keyboard_input`, then wait for the tween and take a `screen_capture`.
   - Press E again, check that the lid closes, read `get_console_output` for errors, then stop play.
   - If the lid swings the wrong way or flips, fix the rotation direction or axis and test again.

**Don't save the place.**

Then report a checklist to me: ✅ or ❌ for found, setup, textures, hinge, script and playtest, with a one-line note for each and the chest's size in studs.
