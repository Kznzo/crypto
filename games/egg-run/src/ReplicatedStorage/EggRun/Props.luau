--!strict
-- Egg Run: props for the map and the UI.
-- Uses the voxel kit made in Blender (ReplicatedStorage.EggRunKit, imported from
-- assets/EggRunKit.glb) and the Voxel Stud Egg Pack (ReplicatedStorage.EggPack)
-- when they are in the place. Without them, every prop is built from blocks in
-- the same size and colours, so the map always works.
-- Install: ReplicatedStorage/EggRun/Props (ModuleScript)

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(script.Parent:WaitForChild("Config"))

local Props = {}

-- Real heights (studs) of the kit pieces, used to scale any import to size.
Props.KitHeights = {
	VBush = 5, VBushSmall = 3, VCactus = 8, VRock = 3, VTree = 13, VPalm = 15, VPine = 15,
	VHay = 3, VFlower = 3, VIce = 7, VLavaRock = 4, VCloud = 4, VCrystal = 10, VPillar = 15,
	LBarn = 24, LBeehive = 28, LRainbow = 30, LSnowman = 46, LVolcano = 31.2, LPyramid = 28,
} :: { [string]: number }

-- Painted near-white in Blender: their colour comes from the tint.
Props.Tintable = { VRock = true, VIce = true, VCrystal = true } :: { [string]: boolean }

-- Landmarks that are a bigger copy of a small piece.
Props.Aliases = {
	LBigTree = { piece = "VTree", scale = 3.2 },
	LStormCloud = { piece = "VCloud", scale = 6, float = 34 },
	LBigCrystal = { piece = "VCrystal", scale = 4.2, tint = Color3.fromRGB(170, 120, 255) },
} :: { [string]: { piece: string, scale: number, float: number?, tint: Color3? } }

local WHITE = Color3.new(1, 1, 1)

local function kitFolder(): Instance?
	return ReplicatedStorage:FindFirstChild("EggRunKit")
end

local function eggFolder(): Instance?
	return ReplicatedStorage:FindFirstChild(Config.EggPackFolder)
end

function Props.HasKit(): boolean
	return kitFolder() ~= nil
end

function Props.HasEggPack(): boolean
	return eggFolder() ~= nil
end

---------------------------------------------------------------------------
-- Block fallbacks (voxel look). Boxes are { x0, y0, z0, x1, y1, z1, colour }
-- in voxel cells, z up as in Blender; converted to Roblox (Y up) here.
---------------------------------------------------------------------------
type Box = { any }

local function rgb(r: number, g: number, b: number): Color3
	return Color3.fromRGB(r, g, b)
end

local GREEN, GREEN_D, GREEN_L = rgb(90, 190, 70), rgb(62, 150, 52), rgb(130, 215, 95)
local TRUNK, TRUNK_D = rgb(140, 92, 56), rgb(110, 70, 44)
local PINE, SNOW = rgb(46, 125, 84), rgb(245, 250, 255)
local HAY, HAY_D = rgb(236, 196, 92), rgb(190, 145, 60)
local HONEY, HONEY_D = rgb(255, 190, 40), rgb(120, 80, 30)
local BASALT, EMBER = rgb(70, 60, 60), rgb(255, 110, 30)
local GOLD, GOLD_D = rgb(255, 205, 60), rgb(225, 165, 40)
local RED, RED_D = rgb(205, 60, 50), rgb(160, 45, 40)
local TINT = "tint" -- placeholder colour replaced by the tint

local recipes: { [string]: { unit: number, boxes: { Box } } } = {
	VBush = { unit = 1, boxes = { { 0, 0, 0, 7, 4, 3, GREEN }, { 1, 0, 3, 5, 4, 5, GREEN_L }, { 5, 1, 0, 9, 4, 2, GREEN_D } } },
	VBushSmall = { unit = 1, boxes = { { 0, 0, 0, 4, 3, 2, GREEN }, { 1, 0, 2, 3, 3, 3, GREEN_L } } },
	VCactus = { unit = 1, boxes = { { 0, 0, 0, 1, 1, 8, GREEN_D }, { 1, 0, 3, 3, 1, 4, GREEN_D }, { 2, 0, 4, 3, 1, 6, GREEN_D }, { -2, 0, 2, 0, 1, 3, GREEN_D }, { -2, 0, 3, -1, 1, 5, GREEN_D } } },
	VRock = { unit = 1, boxes = { { 0, 0, 0, 4, 3, 2, TINT }, { 1, 0, 2, 3, 3, 3, TINT }, { 4, 1, 0, 5, 3, 1, TINT } } },
	VTree = { unit = 1, boxes = { { 0, 0, 0, 2, 2, 6, TRUNK }, { -3, -3, 6, 5, 5, 10, GREEN }, { -2, -2, 10, 4, 4, 11, GREEN }, { -1, -1, 11, 3, 3, 13, GREEN_L } } },
	VPalm = { unit = 1, boxes = { { 0, 0, 0, 1, 1, 6, TRUNK }, { 1, 0, 5, 2, 1, 12, TRUNK_D }, { 2, 0, 11, 3, 1, 14, TRUNK }, { -2, 0, 14, 7, 1, 15, GREEN }, { 2, -4, 14, 3, 5, 15, GREEN }, { 1, -1, 14, 4, 2, 15, GREEN_D } } },
	VPine = { unit = 1, boxes = { { 0, 0, 0, 1, 1, 3, TRUNK_D }, { -4, -4, 3, 5, 5, 6, PINE }, { -3, -3, 6, 4, 4, 9, PINE }, { -2, -2, 9, 3, 3, 12, PINE }, { -1, -1, 12, 2, 2, 14, PINE }, { -1, -1, 14, 2, 2, 15, SNOW } } },
	VHay = { unit = 1, boxes = { { 0, 0, 0, 4, 3, 3, HAY }, { 1, 0, 0, 2, 3, 3, HAY_D }, { 3, 0, 0, 4, 3, 3, HAY_D } } },
	VFlower = { unit = 1, boxes = { { 1, 1, 0, 2, 2, 2, GREEN_D }, { 0, 1, 2, 3, 2, 3, rgb(255, 120, 170) }, { 1, 0, 2, 2, 3, 3, rgb(255, 120, 170) }, { 1, 1, 2, 2, 2, 3, rgb(255, 220, 60) } } },
	VIce = { unit = 1, boxes = { { 0, 0, 0, 2, 2, 7, TINT }, { 2, 0, 0, 3, 2, 4, TINT }, { -1, 1, 0, 0, 2, 5, TINT } } },
	VLavaRock = { unit = 1, boxes = { { 0, 0, 0, 5, 4, 2, BASALT }, { 1, 1, 2, 4, 3, 3, BASALT }, { 2, 1, 3, 3, 2, 4, EMBER }, { 4, 3, 1, 5, 4, 2, EMBER } } },
	VCloud = { unit = 1, boxes = { { 0, 0, 0, 10, 4, 2, WHITE }, { 2, 0, 2, 7, 4, 4, WHITE }, { 7, 1, 2, 9, 3, 3, WHITE } } },
	VCrystal = { unit = 1, boxes = { { 0, 0, 0, 2, 2, 8, TINT }, { 0, 0, 8, 1, 1, 10, WHITE }, { 2, 0, 0, 3, 2, 3, TINT }, { 3, 0, 2, 4, 2, 5, TINT }, { -1, 1, 0, 0, 2, 4, TINT }, { -2, 1, 3, -1, 2, 6, TINT } } },
	VPillar = { unit = 1, boxes = { { -2, -2, 0, 3, 3, 1, WHITE }, { -1, -1, 1, 2, 2, 12, GOLD }, { -2, -2, 12, 3, 3, 13, WHITE }, { 0, 0, 13, 1, 1, 15, GOLD_D } } },
	LBarn = { unit = 2, boxes = { { 0, 0, 0, 12, 9, 7, RED }, { -1, -1, 7, 13, 10, 8, RED_D }, { 0, -1, 8, 12, 10, 9, RED_D }, { 1, -1, 9, 11, 10, 10, RED_D }, { 2, -1, 10, 10, 10, 11, RED_D }, { 3, -1, 11, 9, 10, 12, RED_D }, { 4, -1, 0, 8, 0, 5, WHITE } } },
	LBeehive = { unit = 2, boxes = { { -6, -6, 0, 7, 7, 2, HONEY }, { -7, -7, 2, 8, 8, 4, HONEY_D }, { -7, -7, 4, 8, 8, 6, HONEY }, { -6, -6, 6, 7, 7, 8, HONEY_D }, { -5, -5, 8, 6, 6, 10, HONEY }, { -3, -3, 10, 4, 4, 12, HONEY_D }, { -1, -1, 12, 2, 2, 14, HONEY } } },
	LSnowman = { unit = 2, boxes = { { -4, -4, 0, 5, 5, 8, SNOW }, { -3, -3, 8, 4, 4, 14, SNOW }, { -2, -2, 14, 3, 3, 19, SNOW }, { 0, -4, 16, 1, -2, 17, rgb(255, 140, 30) }, { -3, -3, 19, 4, 4, 20, rgb(35, 35, 40) }, { -2, -2, 20, 3, 3, 23, rgb(35, 35, 40) } } },
	LVolcano = { unit = 2.6, boxes = { { -11, -11, 0, 12, 12, 3, BASALT }, { -9, -9, 3, 10, 10, 6, BASALT }, { -7, -7, 6, 8, 8, 9, BASALT }, { -5, -5, 9, 6, 6, 11, BASALT }, { -2, -2, 10, 3, 3, 11, EMBER } } },
	LPyramid = { unit = 2, boxes = { { -12, -12, 0, 13, 13, 2, GOLD }, { -10, -10, 2, 11, 11, 4, GOLD_D }, { -8, -8, 4, 9, 9, 6, GOLD }, { -6, -6, 6, 7, 7, 8, GOLD_D }, { -4, -4, 8, 5, 5, 10, GOLD }, { -2, -2, 10, 3, 3, 12, GOLD_D }, { 0, 0, 12, 1, 1, 14, GOLD } } },
}

local RAINBOW = { rgb(240, 70, 70), rgb(255, 150, 50), rgb(255, 220, 60), rgb(90, 200, 90), rgb(70, 150, 255), rgb(150, 90, 230) }

local function newBlock(size: Vector3, cf: CFrame, color: Color3, material: Enum.Material?): Part
	local p = Instance.new("Part")
	p.Anchored = true
	p.TopSurface = Enum.SurfaceType.Smooth
	p.BottomSurface = Enum.SurfaceType.Smooth
	p.Material = material or Enum.Material.SmoothPlastic
	p.Size = size
	p.CFrame = cf
	p.Color = color
	return p
end

local function buildRecipe(name: string, tint: Color3): Model
	local m = Instance.new("Model")
	m.Name = name
	if name == "LRainbow" then
		-- arcs of coloured blocks
		for k, c in RAINBOW do
			local radius = (14 - (k - 1)) * 2
			for a = 0, 180, 9 do
				local x = radius * math.cos(math.rad(a))
				local y = radius * math.sin(math.rad(a))
				newBlock(Vector3.new(2.6, 2.6, 4), CFrame.new(x, y + 1.3, 0), c).Parent = m
			end
		end
		return m
	end
	local recipe = recipes[name]
	assert(recipe, `Props: no kit piece '{name}'`)
	local u = recipe.unit
	for _, b in recipe.boxes do
		local color: Color3 = if b[7] == TINT then tint else b[7]
		local x0, y0, z0, x1, y1, z1 = b[1], b[2], b[3], b[4], b[5], b[6]
		-- Blender (x, y, z-up) -> Roblox (x, y-up, -y)
		local size = Vector3.new(x1 - x0, z1 - z0, y1 - y0) * u
		local center = Vector3.new((x0 + x1) / 2, (z0 + z1) / 2, -(y0 + y1) / 2) * u
		local material = if color == EMBER then Enum.Material.Neon else Enum.Material.SmoothPlastic
		newBlock(size, CFrame.new(center), color, material).Parent = m
	end
	return m
end

---------------------------------------------------------------------------
-- Public API
---------------------------------------------------------------------------

-- Every BasePart in `inst` (including itself) as decoration: anchored, no physics queries.
function Props.MakeDecor(inst: Instance, castShadow: boolean?)
	local function apply(p: BasePart)
		p.Anchored = true
		p.CanCollide = false
		p.CanTouch = false
		p.CanQuery = false
		p.CastShadow = castShadow == true
	end
	if inst:IsA("BasePart") then
		apply(inst)
	end
	for _, d in inst:GetDescendants() do
		if d:IsA("BasePart") then
			apply(d)
		end
	end
end

local function heightOf(inst: PVInstance): number
	if inst:IsA("Model") then
		local _, size = inst:GetBoundingBox()
		return size.Y
	end
	return (inst :: BasePart).Size.Y
end

local function scaleBy(inst: PVInstance, factor: number)
	if math.abs(factor - 1) < 1e-3 then
		return
	end
	if inst:IsA("Model") then
		inst:ScaleTo(inst:GetScale() * factor)
	else
		local p = inst :: BasePart
		p.Size *= factor
	end
end

-- A kit prop (or landmark) as a fresh Model or MeshPart, scaled and tinted.
-- Not parented and not placed: use Props.PlaceOnFloor.
function Props.Kit(name: string, scale: number?, tint: Color3?): PVInstance
	local alias = Props.Aliases[name]
	if alias then
		local inst = Props.Kit(alias.piece, alias.scale * (scale or 1), tint or alias.tint)
		inst.Name = name
		return inst
	end
	local target = (Props.KitHeights[name] or 4) * (scale or 1)
	local color = tint or Color3.fromRGB(200, 200, 205)
	local folder = kitFolder()
	local source = folder and folder:FindFirstChild(name, true)
	local inst: PVInstance
	if source and (source:IsA("BasePart") or source:IsA("Model")) then
		inst = source:Clone() :: PVInstance
		local parts: { BasePart } = {}
		if inst:IsA("BasePart") then
			table.insert(parts, inst)
		end
		for _, d in inst:GetDescendants() do
			if d:IsA("BasePart") then
				table.insert(parts, d)
			end
		end
		for _, p in parts do
			-- Vertex colours multiply with Color: white shows the painted colours;
			-- a tint colours the near-white pieces.
			p.Color = if Props.Tintable[name] then color else WHITE
		end
	else
		inst = buildRecipe(name, color)
	end
	inst.Name = name
	local h = heightOf(inst)
	if h > 0 then
		scaleBy(inst, target / h)
	end
	return inst
end

-- Height above the floor a landmark floats at (clouds), or 0.
function Props.FloatHeight(name: string): number
	local alias = Props.Aliases[name]
	return if alias and alias.float then alias.float else 0
end

-- Moves `inst` so the bottom of its bounding box rests on `floorY` at (x, z), turned by `yaw` radians.
function Props.PlaceOnFloor(inst: PVInstance, x: number, floorY: number, z: number, yaw: number?)
	inst:PivotTo(CFrame.new(x, floorY, z) * CFrame.Angles(0, yaw or 0, 0))
	local bottom: number
	if inst:IsA("Model") then
		local cf, size = inst:GetBoundingBox()
		bottom = cf.Position.Y - size.Y / 2
	else
		local p = inst :: BasePart
		bottom = p.Position.Y - p.Size.Y / 2
	end
	inst:PivotTo(inst:GetPivot() + Vector3.new(0, floorY - bottom, 0))
end

-- Width (X) and depth (Z) of a prop's bounding box.
function Props.Footprint(inst: PVInstance): Vector3
	if inst:IsA("Model") then
		local _, size = inst:GetBoundingBox()
		return size
	end
	return (inst :: BasePart).Size
end

-- An egg model `height` studs tall: the pack's model when available, else a painted egg.
-- keepHighlight = false removes the pack's Highlight (Roblox draws at most 31 at once).
function Props.Egg(eggId: string, height: number, keepHighlight: boolean?): Model
	local def = Config.Eggs[eggId]
	local folder = eggFolder()
	local source = folder and folder:FindFirstChild(eggId)
	local egg: Model
	if source and source:IsA("Model") then
		egg = source:Clone()
		for _, d in egg:GetDescendants() do
			if d:IsA("LuaSourceContainer") then
				d:Destroy() -- props only: never run scripts that came with a pack
			elseif d:IsA("Highlight") and keepHighlight == false then
				d:Destroy()
			end
		end
	else
		egg = Instance.new("Model")
		local color = if def then def.color else Color3.fromRGB(240, 240, 240)
		-- a blocky egg: stacked slabs, widest in the lower middle
		local rows = { { 3, 0 }, { 4, 1 }, { 4, 2 }, { 4, 3 }, { 3, 4 }, { 2, 5 } }
		for _, row in rows do
			local w = row[1]
			newBlock(Vector3.new(w, 1, w), CFrame.new(0, row[2] + 0.5, 0), color).Parent = egg
		end
		newBlock(Vector3.new(0.8, 0.8, 0.2), CFrame.new(-0.8, 3.2, -2.05), WHITE).Parent = egg
		newBlock(Vector3.new(0.8, 0.8, 0.2), CFrame.new(0.9, 1.8, -2.05), WHITE).Parent = egg
	end
	egg.Name = eggId
	local _, size = egg:GetBoundingBox()
	if size.Y > 0 then
		egg:ScaleTo(egg:GetScale() * height / size.Y)
	end
	return egg
end

return Props
