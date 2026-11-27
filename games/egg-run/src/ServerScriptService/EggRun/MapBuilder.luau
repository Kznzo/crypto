--!strict
-- Egg Run: builds Workspace.EggRunMap from Config + Layout.
-- Install: ServerScriptService/EggRun/MapBuilder (ModuleScript)
--
-- In Studio (Edit mode), command bar:
--     require(game.ServerScriptService.EggRun.MapBuilder).Build()
-- At runtime Main calls MapBuilder.EnsureBuilt(), which builds only if the map is missing.
--
-- Layout follows the LihFolk worldbuilding method: one folder per pass
-- (01_Layout, 02_Primary, 03_Medium, 04_Detail), walkable floors tagged
-- LF_Ground, paths tagged LF_NoScatter, floating props tagged LF_AllowFloat.
-- The look: a wide canyon with checkerboard walls topped by a coloured cap,
-- a checkered floor, voxel props along the walls and the centre kept clear.

local CollectionService = game:GetService("CollectionService")
local Lighting = game:GetService("Lighting")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Workspace = game:GetService("Workspace")

local Shared = ReplicatedStorage:WaitForChild("EggRun")
local Config = require(Shared:WaitForChild("Config"))
local Layout = require(Shared:WaitForChild("Layout"))
local Props = require(Shared:WaitForChild("Props"))

local MapBuilder = {}
MapBuilder.MapName = "EggRunMap"

-- Grid overlay texture from the Voxel Stud Egg Pack's baseplate (10-stud tiles).
local GRID_TEXTURE = "rbxassetid://12232620641"

local WHITE = Color3.new(1, 1, 1)
local CREAM = Color3.fromRGB(250, 240, 214)
local GRASS = Color3.fromRGB(95, 200, 70)
local GRASS2 = Color3.fromRGB(84, 186, 62)

---------------------------------------------------------------------------
-- Helpers
---------------------------------------------------------------------------

local function folder(name: string, parent: Instance): Folder
	local f = Instance.new("Folder")
	f.Name = name
	f.Parent = parent
	return f
end

local function part(parent: Instance, size: Vector3, cframe: CFrame, color: Color3, material: Enum.Material?, name: string?): Part
	local p = Instance.new("Part")
	p.Anchored = true
	p.TopSurface = Enum.SurfaceType.Smooth
	p.BottomSurface = Enum.SurfaceType.Smooth
	p.Material = material or Enum.Material.SmoothPlastic
	p.Size = size
	p.CFrame = cframe
	p.Color = color
	if name then
		p.Name = name
	end
	p.Parent = parent
	return p
end

local function cylinderUp(parent: Instance, radius: number, height: number, bottom: Vector3, color: Color3, material: Enum.Material?, name: string?): Part
	local p = part(parent, Vector3.new(height, radius * 2, radius * 2), CFrame.new(bottom + Vector3.new(0, height / 2, 0)) * CFrame.Angles(0, 0, math.rad(90)), color, material, name)
	p.Shape = Enum.PartType.Cylinder
	return p
end

local function decor(inst: Instance, castShadow: boolean?)
	Props.MakeDecor(inst, castShadow)
end

local function tag(inst: Instance, tagName: string)
	CollectionService:AddTag(inst, tagName)
end

local function materialNamed(name: string): Enum.Material
	local ok, material = pcall(function()
		return (Enum.Material :: any)[name]
	end)
	return if ok and material then material else Enum.Material.SmoothPlastic
end

-- A board with text on the front (and back), e.g. signs and banners.
local function sign(parent: Instance, size: Vector3, cframe: CFrame, text: string, board: Color3, textColor: Color3?, name: string?): Part
	local p = part(parent, size, cframe, board, Enum.Material.SmoothPlastic, name or "Sign")
	for _, face in { Enum.NormalId.Front, Enum.NormalId.Back } do
		local gui = Instance.new("SurfaceGui")
		gui.Face = face
		gui.SizingMode = Enum.SurfaceGuiSizingMode.PixelsPerStud
		gui.PixelsPerStud = 40
		gui.LightInfluence = 0.2
		local label = Instance.new("TextLabel")
		label.Name = "Text"
		label.BackgroundTransparency = 1
		label.Size = UDim2.fromScale(1, 1)
		label.Font = Enum.Font.FredokaOne
		label.TextScaled = true
		label.TextColor3 = textColor or WHITE
		label.Text = text
		local stroke = Instance.new("UIStroke")
		stroke.Thickness = 4
		stroke.Color = Color3.fromRGB(40, 40, 50)
		stroke.Parent = label
		local pad = Instance.new("UIPadding")
		pad.PaddingTop = UDim.new(0.08, 0)
		pad.PaddingBottom = UDim.new(0.08, 0)
		pad.PaddingLeft = UDim.new(0.04, 0)
		pad.PaddingRight = UDim.new(0.04, 0)
		pad.Parent = label
		label.Parent = gui
		gui.Parent = p
	end
	return p
end

local function billboard(adornee: Instance, lines: { { text: string, color: Color3 } }, studsOffset: Vector3, width: number)
	local gui = Instance.new("BillboardGui")
	gui.Name = "Label"
	gui.Size = UDim2.new(width, 0, #lines * 1.4, 0)
	gui.StudsOffset = studsOffset
	gui.AlwaysOnTop = false
	gui.MaxDistance = 400
	gui.LightInfluence = 0
	local list = Instance.new("UIListLayout")
	list.SortOrder = Enum.SortOrder.LayoutOrder
	list.Parent = gui
	for i, line in lines do
		local label = Instance.new("TextLabel")
		label.LayoutOrder = i
		label.BackgroundTransparency = 1
		label.Size = UDim2.fromScale(1, 1 / #lines)
		label.Font = Enum.Font.FredokaOne
		label.TextScaled = true
		label.TextColor3 = line.color
		label.Text = line.text
		local stroke = Instance.new("UIStroke")
		stroke.Thickness = 3
		stroke.Color = Color3.fromRGB(30, 30, 40)
		stroke.Parent = label
		label.Parent = gui
	end
	gui.Parent = adornee
end

-- A transparent part carrying the pack's grid texture on its top face.
local function gridOverlay(parent: Instance, size: Vector3, center: Vector3)
	local p = part(parent, Vector3.new(size.X, 0.05, size.Z), CFrame.new(center), WHITE, Enum.Material.SmoothPlastic, "GridOverlay")
	p.Transparency = 1
	decor(p)
	local t = Instance.new("Texture")
	t.Face = Enum.NormalId.Top
	t.Texture = GRID_TEXTURE
	t.StudsPerTileU = 10
	t.StudsPerTileV = 10
	t.Transparency = 0.8
	t.Parent = p
end

local function place(inst: PVInstance, parent: Instance, x: number, y: number, z: number, yaw: number?, float: boolean?)
	Props.PlaceOnFloor(inst, x, y, z, yaw)
	decor(inst)
	if float then
		tag(inst, "LF_AllowFloat")
	end
	inst.Parent = parent
end

local function highestRarity(weights: { [string]: number }): string
	local best, bestRank = "Common", 0
	for name, w in weights do
		local rank = Config.RarityIndex[name] or 0
		if w > 0 and rank > bestRank then
			best, bestRank = name, rank
		end
	end
	return best
end

---------------------------------------------------------------------------
-- Hub (spawn plaza)
---------------------------------------------------------------------------

local function buildHub(f: { [string]: Folder })
	local minV, maxV = Layout.HubMin, Layout.HubMax
	local size = Vector3.new(maxV.X - minV.X, 2, maxV.Z - minV.Z)
	local center = Vector3.new((minV.X + maxV.X) / 2, -1, (minV.Z + maxV.Z) / 2)
	local ground = part(f.Layout, size, CFrame.new(center), GRASS, Enum.Material.Grass, "HubGround")
	tag(ground, "LF_Ground")
	gridOverlay(f.Layout, size, Vector3.new(center.X, 0.03, center.Z))

	-- Main aisle: arena deck -> spawn -> START arch.
	local aisleStart, aisleEnd = -170, Layout.CorridorStartZ
	local aisle = part(f.Layout, Vector3.new(Layout.AisleHalfWidth * 2, 0.2, aisleEnd - aisleStart), CFrame.new(0, 0.1, (aisleStart + aisleEnd) / 2), CREAM, Enum.Material.SmoothPlastic, "Aisle")
	tag(aisle, "LF_Ground")
	tag(aisle, "LF_NoScatter")

	-- Side paths to each row of bases.
	for row = 1, 3 do
		local z = Layout.PlotCFrame(row).Position.Z
		local width = (104 - Layout.PlotSize / 2) * 2
		local path = part(f.Layout, Vector3.new(width, 0.2, 14), CFrame.new(0, 0.1, z), CREAM, Enum.Material.SmoothPlastic, "BasePath")
		tag(path, "LF_Ground")
		tag(path, "LF_NoScatter")
	end

	-- Spawn pad facing the canyon.
	local spawnLocation = Instance.new("SpawnLocation")
	spawnLocation.Name = "Spawn"
	spawnLocation.Anchored = true
	spawnLocation.Neutral = true
	spawnLocation.Duration = 0
	spawnLocation.Size = Vector3.new(16, 1, 16)
	spawnLocation.CFrame = Layout.Spawn - Vector3.new(0, 0.1, 0)
	spawnLocation.Color = Color3.fromRGB(255, 236, 140)
	spawnLocation.Material = Enum.Material.SmoothPlastic
	spawnLocation.TopSurface = Enum.SurfaceType.Smooth
	local decal = spawnLocation:FindFirstChildOfClass("Decal")
	if decal then
		decal:Destroy()
	end
	spawnLocation.Parent = f.Layout

	-- Voxel lamp posts lead the eye down the aisle to the START arch.
	for z = -160, 20, 30 do
		for _, side in { -1, 1 } do
			local x = side * (Layout.AisleHalfWidth + 3)
			local post = Instance.new("Model")
			post.Name = "Lamp"
			part(post, Vector3.new(1.4, 9, 1.4), CFrame.new(x, 4.5, z), Color3.fromRGB(80, 80, 95))
			part(post, Vector3.new(2.8, 2.8, 2.8), CFrame.new(x, 10.4, z), Color3.fromRGB(255, 236, 150), Enum.Material.Neon)
			decor(post)
			post.Parent = f.Medium
		end
	end

	-- Edge dressing: trees and bushes along the hub borders (never on paths).
	local rng = Random.new(42)
	for x = -220, 220, 22 do
		for _, z in { minV.Z + 8, -230 } do
			if math.abs(x) > 50 then
				local name = if rng:NextNumber() < 0.5 then "VTree" else "VBush"
				place(Props.Kit(name, rng:NextNumber(0.9, 1.3)), f.Medium, x + rng:NextNumber(-4, 4), 0, z + rng:NextNumber(-4, 4), rng:NextNumber(0, math.pi * 2))
			end
		end
	end
	for z = -200, 30, 26 do
		for _, side in { -1, 1 } do
			place(Props.Kit(if rng:NextNumber() < 0.5 then "VBush" else "VFlower", rng:NextNumber(0.9, 1.4)), f.Detail, side * rng:NextNumber(150, 220), 0, z + rng:NextNumber(-6, 6), rng:NextNumber(0, math.pi * 2))
		end
	end

	-- Signposts by the spawn.
	sign(f.Detail, Vector3.new(14, 4, 0.6), CFrame.new(-12, 9, -58) * CFrame.Angles(0, math.rad(15), 0), "RUN FOR EGGS ^", Color3.fromRGB(90, 170, 255))
	sign(f.Detail, Vector3.new(14, 4, 0.6), CFrame.new(12, 9, -86) * CFrame.Angles(0, math.rad(165), 0), "BATTLE BOX v", Color3.fromRGB(240, 90, 90))
	for _, pos in { Vector3.new(-12, 0, -58), Vector3.new(12, 0, -86) } do
		local postPart = part(f.Detail, Vector3.new(1, 7, 1), CFrame.new(pos + Vector3.new(0, 3.5, 0)), Color3.fromRGB(110, 70, 44))
		decor(postPart)
	end

	-- Invisible walls around the hub (the canyon mouth stays open).
	local h = 60
	local function barrier(sizeV: Vector3, pos: Vector3)
		local b = part(f.Layout, sizeV, CFrame.new(pos), WHITE, Enum.Material.SmoothPlastic, "Barrier")
		b.Transparency = 1
		b.CanQuery = false
		b.CastShadow = false
	end
	local half = Config.Corridor.width / 2
	barrier(Vector3.new(2, h, size.Z), Vector3.new(minV.X - 1, h / 2, center.Z))
	barrier(Vector3.new(2, h, size.Z), Vector3.new(maxV.X + 1, h / 2, center.Z))
	barrier(Vector3.new(size.X, h, 2), Vector3.new(center.X, h / 2, minV.Z - 1))
	local sideLen = maxV.X - half
	barrier(Vector3.new(sideLen, h, 2), Vector3.new(-(half + sideLen / 2), h / 2, maxV.Z + 1))
	barrier(Vector3.new(sideLen, h, 2), Vector3.new(half + sideLen / 2, h / 2, maxV.Z + 1))
end

---------------------------------------------------------------------------
-- Bases
---------------------------------------------------------------------------

local function buildPlot(index: number, f: { [string]: Folder })
	local cf = Layout.PlotCFrame(index)
	local S = Layout.PlotSize
	local color = Layout.PlotColors[index]
	local dark = color:Lerp(Color3.new(0, 0, 0), 0.25)
	local plot = Instance.new("Model")
	plot.Name = `Plot{index}`
	plot:SetAttribute("PlotIndex", index)

	part(plot, Vector3.new(S + 3, 1, S + 3), cf * CFrame.new(0, -0.1, 0), dark, Enum.Material.SmoothPlastic, "Trim")
	local floor = part(plot, Vector3.new(S, 1.2, S), cf, color, Enum.Material.SmoothPlastic, "Floor")
	tag(floor, "LF_Ground")

	-- Low voxel wall on the back and both sides (the front faces the aisle).
	local wallParts = Instance.new("Model")
	wallParts.Name = "Wall"
	for _, spec in { { 0, S / 2, S, 2 }, { -S / 2, 0, 2, S }, { S / 2, 0, 2, S } } do
		part(wallParts, Vector3.new(spec[3], 3, spec[4]), cf * CFrame.new(spec[1], 2.1, spec[2]), dark)
	end
	for i = -3, 3 do
		local o = i * (S / 7)
		part(wallParts, Vector3.new(3, 2, 3), cf * CFrame.new(o, 4.6, S / 2), color)
		part(wallParts, Vector3.new(3, 2, 3), cf * CFrame.new(-S / 2, 4.6, o), color)
		part(wallParts, Vector3.new(3, 2, 3), cf * CFrame.new(S / 2, 4.6, o), color)
	end
	wallParts.Parent = plot

	-- Owner sign at the front-left corner, facing the aisle.
	local signCF = cf * CFrame.new(-S / 2 + 9, 8, -S / 2 + 1.5) * CFrame.Angles(0, math.pi, 0)
	local post1 = part(plot, Vector3.new(1, 7, 1), cf * CFrame.new(-S / 2 + 3, 3.5, -S / 2 + 1.5), Color3.fromRGB(110, 70, 44))
	local post2 = part(plot, Vector3.new(1, 7, 1), cf * CFrame.new(-S / 2 + 15, 3.5, -S / 2 + 1.5), Color3.fromRGB(110, 70, 44))
	decor(post1)
	decor(post2)
	local ownerSign = sign(plot, Vector3.new(14, 4, 0.6), signCF, "EMPTY BASE", dark, WHITE, "OwnerSign")
	decor(ownerSign)

	-- Training pad (players stand on it to train their team).
	local padPos = Layout.PlotPad(index)
	local ring = cylinderUp(plot, Config.Training.padRadius, 0.3, padPos + Vector3.new(0, 0.6, 0), color:Lerp(WHITE, 0.35), Enum.Material.Neon, "TrainingPad")
	ring.CanCollide = false
	ring.CanQuery = false
	local inner = cylinderUp(plot, Config.Training.padRadius - 1.5, 0.35, padPos + Vector3.new(0, 0.6, 0), WHITE, Enum.Material.SmoothPlastic, "PadInner")
	inner.CanCollide = false
	inner.CanQuery = false
	billboard(ring, { { text = "TRAINING PAD", color = WHITE }, { text = "stand here to train", color = Color3.fromRGB(220, 240, 255) } }, Vector3.new(0, 6, 0), 12)

	-- Podiums for the team display.
	for i, podiumCF in Layout.PlotPodiums(index) do
		local podium = cylinderUp(plot, 3.2, 2.2, podiumCF.Position + Vector3.new(0, 0.6, 0), WHITE, Enum.Material.SmoothPlastic, `Podium{i}`)
		podium.CanQuery = false
		cylinderUp(plot, 3.6, 0.4, podiumCF.Position + Vector3.new(0, 0.6, 0), color:Lerp(WHITE, 0.2), Enum.Material.Neon).CanCollide = false
	end

	-- Corner dressing inside the wall.
	local rng = Random.new(100 + index)
	for _, corner in { Vector3.new(-S / 2 + 6, 0, S / 2 - 6), Vector3.new(S / 2 - 6, 0, S / 2 - 6) } do
		local world = (cf * CFrame.new(corner)).Position
		place(Props.Kit("VTree", rng:NextNumber(0.9, 1.15)), plot, world.X, 0.6, world.Z, rng:NextNumber(0, math.pi * 2))
	end
	for _, spot in { Vector3.new(-S / 2 + 5, 0, -S / 2 + 12), Vector3.new(S / 2 - 5, 0, -S / 2 + 6), Vector3.new(S / 2 - 6, 0, 8) } do
		local world = (cf * CFrame.new(spot)).Position
		place(Props.Kit(if rng:NextNumber() < 0.5 then "VBush" else "VFlower"), plot, world.X, 0.6, world.Z, rng:NextNumber(0, math.pi * 2))
	end

	plot.Parent = f.Primary
end

---------------------------------------------------------------------------
-- Battle Box (arena)
---------------------------------------------------------------------------

local function buildArena(f: { [string]: Folder })
	local c = Layout.ArenaCenter
	local S = Layout.ArenaSize
	local arena = Instance.new("Model")
	arena.Name = "BattleBox"

	-- Checker floor.
	local n = 7
	local t = S / n
	for ix = 0, n - 1 do
		for iz = 0, n - 1 do
			local col = if (ix + iz) % 2 == 0 then Color3.fromRGB(236, 236, 244) else Color3.fromRGB(200, 204, 220)
			local tile = part(arena, Vector3.new(t, 1, t), CFrame.new(c.X - S / 2 + t * (ix + 0.5), -0.3, c.Z - S / 2 + t * (iz + 0.5)), col, Enum.Material.SmoothPlastic, "ArenaFloor")
			tag(tile, "LF_Ground")
		end
	end
	-- Team pads: yours by the viewing deck (+Z), enemies opposite.
	part(arena, Vector3.new(S - 14, 0.2, 10), CFrame.new(c.X, 0.3, c.Z + 14), Color3.fromRGB(90, 160, 255), Enum.Material.Neon, "TeamPad").CanCollide = false
	part(arena, Vector3.new(S - 14, 0.2, 10), CFrame.new(c.X, 0.3, c.Z - 14), Color3.fromRGB(255, 90, 90), Enum.Material.Neon, "EnemyPad").CanCollide = false

	-- Glass walls and a coloured top rail.
	local H = 30
	for _, spec in { { 0, -S / 2, S, 1 }, { 0, S / 2, S, 1 }, { -S / 2, 0, 1, S }, { S / 2, 0, 1, S } } do
		local wall = part(arena, Vector3.new(spec[3], H, spec[4]), CFrame.new(c.X + spec[1], H / 2, c.Z + spec[2]), Color3.fromRGB(200, 230, 255), Enum.Material.Glass, "Glass")
		wall.Transparency = 0.7
		wall.CastShadow = false
		local rail = part(arena, Vector3.new(math.max(spec[3], 2), 1.5, math.max(spec[4], 2)), CFrame.new(c.X + spec[1], H + 0.75, c.Z + spec[2]), Color3.fromRGB(255, 90, 90))
		decor(rail)
	end
	-- Corner towers (voxel blocks).
	for _, sx in { -1, 1 } do
		for _, sz in { -1, 1 } do
			part(arena, Vector3.new(6, H + 6, 6), CFrame.new(c.X + sx * S / 2, (H + 6) / 2, c.Z + sz * S / 2), Color3.fromRGB(230, 80, 80))
		end
	end

	-- Viewing deck with a ramp down to the aisle.
	local deckZ = c.Z + S / 2 + 8
	local deck = part(arena, Vector3.new(40, 7, 14), CFrame.new(c.X, 3.5, deckZ), Color3.fromRGB(240, 220, 180), Enum.Material.SmoothPlastic, "ViewerDeck")
	tag(deck, "LF_Ground")
	local ramp = Instance.new("WedgePart")
	ramp.Name = "Ramp"
	ramp.Anchored = true
	ramp.Size = Vector3.new(16, 7, 22)
	ramp.CFrame = CFrame.new(c.X, 3.5, deckZ + 7 + 11) * CFrame.Angles(0, math.pi, 0)
	ramp.Color = Color3.fromRGB(240, 220, 180)
	ramp.Material = Enum.Material.SmoothPlastic
	ramp.TopSurface = Enum.SurfaceType.Smooth
	ramp.BottomSurface = Enum.SurfaceType.Smooth
	ramp.Parent = arena
	tag(ramp, "LF_Ground")
	for _, side in { -1, 1 } do
		part(arena, Vector3.new(1, 3, 14), CFrame.new(c.X + side * 19.5, 8.5, deckZ), Color3.fromRGB(255, 90, 90))
	end

	-- Big sign facing the hub.
	sign(arena, Vector3.new(34, 7, 1), CFrame.new(c.X, 20, deckZ - 4) * CFrame.Angles(0, math.pi, 0), "BATTLE BOX", Color3.fromRGB(230, 70, 70))

	-- Two lights over the fight (focal point).
	for _, sx in { -1, 1 } do
		local holder = part(arena, Vector3.new(1, 1, 1), CFrame.new(c.X + sx * 16, H + 6, c.Z), WHITE)
		holder.Transparency = 1
		decor(holder)
		local light = Instance.new("PointLight")
		light.Brightness = 1.6
		light.Range = 50
		light.Shadows = false
		light.Parent = holder
	end

	arena.Parent = f.Primary
end

---------------------------------------------------------------------------
-- The canyon (corridor)
---------------------------------------------------------------------------

local function pickWeighted(list: { { any } }, rng: Random): { any }
	local total = 0
	for _, entry in list do
		total += entry[2]
	end
	local r = rng:NextNumber() * total
	for _, entry in list do
		r -= entry[2]
		if r <= 0 then
			return entry
		end
	end
	return list[#list]
end

local function buildZone(index: number, f: { [string]: Folder })
	local zone = Config.Zones[index]
	local W = Config.Corridor.width
	local half = W / 2
	local H = Config.Corridor.wallHeight
	local T = Config.Corridor.tile
	local z0, z1 = Layout.ZoneRange(index)
	local len = z1 - z0
	local cols = math.max(1, math.round(len / T))
	local tileLen = len / cols
	local label = string.format("%02d_%s", index, zone.name)

	-- 01 Layout: checker floor + grid overlay.
	local floorFolder = folder(label, f.Layout)
	local nx = math.max(1, math.round(W / T))
	local tileW = W / nx
	local floorMaterial = materialNamed(zone.floorMaterial)
	for ix = 0, nx - 1 do
		for iz = 0, cols - 1 do
			local color = if (ix + iz) % 2 == 0 then zone.floor else zone.floor2
			local tile = part(floorFolder, Vector3.new(tileW, 1, tileLen), CFrame.new(-half + tileW * (ix + 0.5), -0.5, z0 + tileLen * (iz + 0.5)), color, floorMaterial, "Floor")
			tag(tile, "LF_Ground")
		end
	end
	gridOverlay(floorFolder, Vector3.new(W, 0, len), Vector3.new(0, 0.03, (z0 + z1) / 2))

	-- 02 Primary: checkerboard walls with a cap strip.
	local wallFolder = folder(label, f.Primary)
	local rows = math.max(1, math.round(H / T))
	local rowH = H / rows
	local capMaterial = if zone.cap == Color3.fromRGB(255, 110, 30) then Enum.Material.Neon
		elseif zone.cap.G > zone.cap.R and zone.cap.G > zone.cap.B then Enum.Material.Grass
		else Enum.Material.SmoothPlastic
	for _, side in { -1, 1 } do
		local x = side * (half + 1)
		for r = 0, rows - 1 do
			for iz = 0, cols - 1 do
				local color = if (r + iz + (if side == 1 then 1 else 0)) % 2 == 0 then zone.wall else zone.wall2
				part(wallFolder, Vector3.new(2, rowH, tileLen), CFrame.new(x, rowH * (r + 0.5), z0 + tileLen * (iz + 0.5)), color, Enum.Material.SmoothPlastic, "Wall")
			end
		end
		part(wallFolder, Vector3.new(8, 3, len), CFrame.new(side * (half + 1), H + 1.5, (z0 + z1) / 2), zone.cap, capMaterial, "Cap")
	end

	-- Zone banner across the top + the zone's egg hovering over the threshold.
	if index > 1 then
		local banner = sign(wallFolder, Vector3.new(W + 4, 9, 3), CFrame.new(0, H - 6, z0), `ZONE {index}  {string.upper(zone.name)}`, zone.cap:Lerp(zone.wall, 0.3), WHITE, "ZoneBanner")
		decor(banner)
		local line = part(wallFolder, Vector3.new(W, 0.2, 2), CFrame.new(0, 0.1, z0), zone.eggColor, Enum.Material.Neon, "ZoneLine")
		decor(line)
	end
	local egg = Props.Egg(zone.egg, 12, true)
	egg:PivotTo(CFrame.new(0, 26, z0 + 8))
	decor(egg)
	tag(egg, "LF_AllowFloat")
	tag(egg, "EggRunSpin")
	local best = highestRarity(zone.weights)
	local bestColor = Config.Rarities[Config.RarityIndex[best]].color
	local anchor = egg.PrimaryPart or egg:FindFirstChildWhichIsA("BasePart", true)
	if anchor then
		billboard(anchor, { { text = zone.eggName, color = WHITE }, { text = `up to {best}`, color = bestColor } }, Vector3.new(0, 11, 0), 18)
	end
	egg.Parent = wallFolder
	local spot = cylinderUp(wallFolder, 10, 0.25, Vector3.new(0, 0, z0 + 8), zone.eggColor, Enum.Material.Neon, "EggSpot")
	decor(spot)

	-- 03 Medium: the zone landmark, on alternating sides (the rainbow spans the run).
	local mediumFolder = folder(label, f.Medium)
	local landmark = Props.Kit(zone.landmark)
	local lmSize = Props.Footprint(landmark)
	local lmZ = z0 + 40 + lmSize.Z / 2
	local lmSide = if index % 2 == 0 then 1 else -1
	local lmX = if zone.landmark == "LRainbow" then 0 else lmSide * (half - math.max(lmSize.X, lmSize.Z) / 2 - 3)
	local yaw = if zone.landmark == "LRainbow" then 0 else lmSide * math.rad(90)
	local float = Props.FloatHeight(zone.landmark)
	place(landmark, mediumFolder, lmX, float, lmZ, yaw, float > 0)
	local lmHalfDepth = math.max(lmSize.X, lmSize.Z) / 2 + 6

	-- Volcano: glowing lava pools along the walls.
	if zone.name == "Volcano" then
		for z = z0 + 30, z1 - 30, 70 do
			for _, side in { -1, 1 } do
				local pool = part(mediumFolder, Vector3.new(14, 0.3, 22), CFrame.new(side * (half - 12), 0.15, z), Color3.fromRGB(255, 110, 30), Enum.Material.Neon, "LavaPool")
				decor(pool)
			end
		end
	end

	-- 04 Detail: voxel props along both walls, centre kept clear.
	local detailFolder = folder(label, f.Detail)
	local rng = Random.new(1000 + index)
	local clear = Config.Corridor.clearHalfWidth
	local z = z0 + 24
	while z < z1 - 8 do
		for _, side in { -1, 1 } do
			local nearLandmark = zone.landmark ~= "LRainbow" and side == lmSide and math.abs(z - lmZ) < lmHalfDepth
			if not nearLandmark and rng:NextNumber() < 0.85 then
				local entry = pickWeighted(zone.props, rng)
				local name: string = entry[1]
				local tint: Color3? = entry[3]
				local s = rng:NextNumber(0.85, 1.15) * (if rng:NextNumber() < 0.15 then 1.6 else 1)
				local inst = Props.Kit(name, s, tint)
				local x = side * rng:NextNumber(clear + 6, half - 5)
				local floatY = if name == "VCloud" then rng:NextNumber(16, 30) else 0
				place(inst, detailFolder, x, floatY, z + rng:NextNumber(-5, 5), rng:NextNumber(0, math.pi * 2), floatY > 0)
			end
		end
		z += rng:NextNumber(14, 24)
	end

	-- Distance markers on the left wall every 100 studs.
	local origin = Config.Corridor.origin.Z
	local first = math.ceil((z0 - origin) / 100) * 100
	for d = math.max(100, first), (z1 - origin) - 1, 100 do
		local marker = sign(detailFolder, Vector3.new(0.4, 6, 12), CFrame.new(-half + 0.25, 9, origin + d) * CFrame.Angles(0, math.rad(90), 0), tostring(d), Color3.fromRGB(255, 255, 255), Color3.fromRGB(60, 60, 80), "DistanceMarker")
		decor(marker)
	end
end

local function buildStartAndEnd(f: { [string]: Folder })
	local W = Config.Corridor.width
	local H = Config.Corridor.wallHeight
	local startZ, endZ = Layout.CorridorStartZ, Layout.CorridorEndZ

	-- START: banner over the canyon mouth with the giant Golden Egg on top (the hero).
	local gold = Color3.fromRGB(255, 205, 60)
	local banner = sign(f.Primary, Vector3.new(W + 12, 14, 6), CFrame.new(0, H - 3, startZ), "RUN FOR EGGS!", gold, WHITE, "StartBanner")
	decor(banner)
	for _, side in { -1, 1 } do
		local tower = part(f.Primary, Vector3.new(10, H + 10, 10), CFrame.new(side * (W / 2 + 5), (H + 10) / 2, startZ), Color3.fromRGB(240, 190, 60), Enum.Material.SmoothPlastic, "StartTower")
		tower.CanQuery = false
	end
	local hero = Props.Egg("GoldenEgg", 34, true)
	Props.PlaceOnFloor(hero, 0, H + 4, startZ)
	decor(hero)
	tag(hero, "LF_AllowFloat")
	tag(hero, "EggRunSpin")
	hero.Name = "HeroEgg"
	hero.Parent = f.Primary
	local heroLight = part(f.Primary, Vector3.new(1, 1, 1), CFrame.new(0, H + 20, startZ - 12), WHITE)
	heroLight.Transparency = 1
	decor(heroLight)
	local light = Instance.new("PointLight")
	light.Brightness = 2
	light.Range = 40
	light.Color = Color3.fromRGB(255, 230, 150)
	light.Parent = heroLight
	local startLine = part(f.Primary, Vector3.new(W, 0.2, 3), CFrame.new(0, 0.1, startZ + 1.5), WHITE, Enum.Material.Neon, "StartLine")
	decor(startLine)

	-- END: golden wall, sign and a big Golden Egg on a pedestal.
	local endWall = part(f.Primary, Vector3.new(W + 4, H, 4), CFrame.new(0, H / 2, endZ + 2), Color3.fromRGB(250, 215, 100), Enum.Material.SmoothPlastic, "EndWall")
	endWall.CanQuery = false
	local endSign = sign(f.Primary, Vector3.new(60, 10, 1), CFrame.new(0, 40, endZ - 0.6), "YOU MADE IT TO THE END!", gold, WHITE, "EndSign")
	decor(endSign)
	cylinderUp(f.Primary, 8, 4, Vector3.new(0, 0, endZ - 20), Color3.fromRGB(255, 245, 220), Enum.Material.SmoothPlastic, "EndPedestal")
	local finalEgg = Props.Egg("GoldenEgg", 20, true)
	Props.PlaceOnFloor(finalEgg, 0, 4, endZ - 20)
	decor(finalEgg)
	tag(finalEgg, "EggRunSpin")
	finalEgg.Parent = f.Primary
end

---------------------------------------------------------------------------
-- Lighting: "Bright cartoon" preset (LihFolk Stylized Lighting Recipes)
---------------------------------------------------------------------------

function MapBuilder.ApplyLighting()
	Lighting.ClockTime = 13.5
	Lighting.Brightness = 2.5
	Lighting.Ambient = Color3.fromRGB(110, 110, 125)
	Lighting.OutdoorAmbient = Color3.fromRGB(150, 150, 160)
	Lighting.EnvironmentDiffuseScale = 1
	Lighting.EnvironmentSpecularScale = 0.4
	Lighting.GlobalShadows = true
	pcall(function()
		(Lighting :: any).PrioritizeLightingQuality = true
	end)

	local atmosphere = Lighting:FindFirstChildOfClass("Atmosphere") or Instance.new("Atmosphere")
	atmosphere.Density = 0.18 -- light haze; far landmarks still read
	atmosphere.Offset = 0.1
	atmosphere.Haze = 0.5
	atmosphere.Glare = 0
	atmosphere.Color = Color3.fromRGB(200, 225, 255)
	atmosphere.Decay = Color3.fromRGB(110, 150, 220)
	atmosphere.Parent = Lighting

	local function effect(className: string, name: string): Instance
		local existing = Lighting:FindFirstChild(name)
		if existing and existing:IsA(className) then
			return existing
		end
		local created = Instance.new(className :: any)
		created.Name = name
		created.Parent = Lighting
		return created
	end
	local grade = effect("ColorCorrectionEffect", "EggRunGrade") :: ColorCorrectionEffect
	grade.Contrast = 0.08
	grade.Saturation = 0.15
	grade.Brightness = 0.02
	local bloom = effect("BloomEffect", "EggRunBloom") :: BloomEffect
	bloom.Intensity = 0.5
	bloom.Size = 24
	bloom.Threshold = 1.6
end

---------------------------------------------------------------------------
-- Public API
---------------------------------------------------------------------------

-- Builds the whole map (replacing an existing one) and applies the lighting.
function MapBuilder.Build(): Model
	-- A pack folder pasted into Workspace is moved to ReplicatedStorage.
	local packInWorkspace = Workspace:FindFirstChild(Config.EggPackFolder)
	if packInWorkspace and not ReplicatedStorage:FindFirstChild(Config.EggPackFolder) then
		packInWorkspace.Parent = ReplicatedStorage
	end
	local kitInWorkspace = Workspace:FindFirstChild("EggRunKit")
	if kitInWorkspace and not ReplicatedStorage:FindFirstChild("EggRunKit") then
		kitInWorkspace.Parent = ReplicatedStorage
	end

	local old = Workspace:FindFirstChild(MapBuilder.MapName)
	if old then
		old:Destroy()
	end
	local map = Instance.new("Model")
	map.Name = MapBuilder.MapName
	local f = {
		Layout = folder("01_Layout", map),
		Primary = folder("02_Primary", map),
		Medium = folder("03_Medium", map),
		Detail = folder("04_Detail", map),
	}
	buildHub(f)
	for i = 1, Config.World.plotCount do
		buildPlot(i, f)
	end
	buildArena(f)
	for i = 1, #Config.Zones do
		buildZone(i, f)
	end
	buildStartAndEnd(f)
	map:SetAttribute("BuiltWithKit", Props.HasKit())
	map:SetAttribute("BuiltWithEggPack", Props.HasEggPack())
	map.Parent = Workspace
	MapBuilder.ApplyLighting()
	return map
end

-- Runtime: returns the existing map, or builds it when missing.
function MapBuilder.EnsureBuilt(): Model
	local existing = Workspace:FindFirstChild(MapBuilder.MapName)
	if existing and existing:IsA("Model") then
		return existing
	end
	return MapBuilder.Build()
end

-- The OwnerSign text label of a plot (for the Plots service).
function MapBuilder.GetPlotModel(index: number): Model?
	local map = Workspace:FindFirstChild(MapBuilder.MapName)
	local primary = map and map:FindFirstChild("02_Primary")
	local plot = primary and primary:FindFirstChild(`Plot{index}`)
	return if plot and plot:IsA("Model") then plot else nil
end

return MapBuilder
