---
description: Smoke-test the blender agent in your open Blender (safe, touches only a Claude_Test collection)
---

Use the **blender** agent to run this smoke test in my open Blender. Give it these instructions:

1. **Connection:** call `get_objects_summary`. Use `execute_blender_code` to return the Blender version (`bpy.app.version_string`), the open file's path (or "unsaved") and the object count. If the tools are missing or can't connect, stop and give me the troubleshooting steps from your instructions.
2. **Skills:** check that the `blender-skills` plugin skills are available (for example `blender-skills:blender-modeling-modifiers`) and load the modelling one. Report whether it loaded.
3. **Build:** create a new collection named `Claude_Test`. Inside it **only**, model a small low-poly stylised mushroom (stem plus cap, under 1,000 triangles) with two simple materials. Put it 3 m to the side of the world origin so it doesn't overlap my objects. Don't change, move, select-and-edit or delete anything else, and don't save the file.
4. **Verify:** frame the mushroom with `jump_to_view3d_object_by_name` and take a screenshot of the 3D Viewport. If there's no window, use `render_thumbnail_to_path` instead. Look at the image and check that it looks like a mushroom.
5. **Roblox check:** report the mushroom's evaluated triangle count and whether it would pass Roblox's per-mesh limit. Don't export anything.

Then report a checklist to me: ✅ or ❌ for connection, skills, build, verify and Roblox check, with a one-line note for each. End by telling me I can say "delete the Claude_Test collection" to remove the test object.
