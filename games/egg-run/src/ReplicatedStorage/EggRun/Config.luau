--!strict
-- Egg Run: every tunable number lives here.
-- Shared with clients, so keep it display-safe: no secrets, no server-only state.
-- Install: ReplicatedStorage/EggRun/Config (ModuleScript)

export type Rarity = {
	name: string,
	color: Color3,
	power: number, -- base power of an animal of this rarity
	health: number, -- base health
	speedBonus: number, -- WalkSpeed added while the animal is on the team
	sell: number, -- coins for releasing it
}

export type Look = {
	body: Color3,
	accent: Color3,
	ears: string, -- "pointy" | "round" | "long" | "floppy" | "none"
	tail: string, -- "none" | "short" | "fluffy" | "long" | "curly"
	extra: string?, -- "beak" | "mane" | "stripes" | "horn"
	scale: number?,
}

export type Animal = {
	id: string,
	name: string,
	rarity: string,
	powerMul: number, -- per-animal tweak around the rarity base (0.9 .. 1.1)
	healthMul: number,
	look: Look,
}

export type Zone = {
	start: number, -- distance (studs) from the corridor start where this zone begins
	name: string,
	egg: string, -- egg id = model name in the Voxel Stud Egg Pack
	eggName: string,
	eggColor: Color3,
	floor: Color3,
	floor2: Color3,
	floorMaterial: string,
	wall: Color3,
	wall2: Color3,
	cap: Color3,
	props: { { any } },
	landmark: string,
	weights: { [string]: number }, -- rarity -> weight for this zone's egg
}

local Config = {}

-- Bump when the saved shape changes (and add a migration in Main).
Config.StoreName = "EggRun_PlayerData_v1"
Config.SchemaVersion = 1

---------------------------------------------------------------------------
-- Rarities, lowest first. Order matters (rank 1 = Common).
---------------------------------------------------------------------------
Config.Rarities = {
	{ name = "Common", color = Color3.fromRGB(190, 190, 190), power = 10, health = 60, speedBonus = 1, sell = 5 },
	{ name = "Uncommon", color = Color3.fromRGB(96, 214, 96), power = 22, health = 132, speedBonus = 2, sell = 12 },
	{ name = "Rare", color = Color3.fromRGB(70, 150, 255), power = 48, health = 288, speedBonus = 3, sell = 30 },
	{ name = "Epic", color = Color3.fromRGB(176, 90, 255), power = 105, health = 630, speedBonus = 5, sell = 80 },
	{ name = "Legendary", color = Color3.fromRGB(255, 196, 40), power = 230, health = 1380, speedBonus = 8, sell = 250 },
	{ name = "Mythic", color = Color3.fromRGB(255, 80, 170), power = 520, health = 3120, speedBonus = 12, sell = 800 },
} :: { Rarity }

Config.RarityIndex = {} :: { [string]: number }
for i, r in Config.Rarities do
	Config.RarityIndex[r.name] = i
end

---------------------------------------------------------------------------
-- Animals: 4 per rarity. Looks are built from simple parts (AnimalModels).
---------------------------------------------------------------------------
local function rgb(r: number, g: number, b: number): Color3
	return Color3.fromRGB(r, g, b)
end

Config.Animals = {
	-- Common
	{ id = "Puppy", name = "Puppy", rarity = "Common", powerMul = 1.0, healthMul = 1.05, look = { body = rgb(196, 140, 90), accent = rgb(245, 225, 200), ears = "floppy", tail = "short" } },
	{ id = "Kitten", name = "Kitten", rarity = "Common", powerMul = 1.08, healthMul = 0.95, look = { body = rgb(240, 160, 80), accent = rgb(255, 235, 210), ears = "pointy", tail = "long" } },
	{ id = "Bunny", name = "Bunny", rarity = "Common", powerMul = 0.95, healthMul = 1.0, look = { body = rgb(245, 245, 245), accent = rgb(255, 190, 200), ears = "long", tail = "fluffy" } },
	{ id = "Chick", name = "Chick", rarity = "Common", powerMul = 0.92, healthMul = 0.92, look = { body = rgb(255, 225, 70), accent = rgb(255, 150, 40), ears = "none", tail = "none", extra = "beak", scale = 0.85 } },
	-- Uncommon
	{ id = "Fox", name = "Fox", rarity = "Uncommon", powerMul = 1.1, healthMul = 0.95, look = { body = rgb(235, 110, 40), accent = rgb(255, 245, 235), ears = "pointy", tail = "fluffy" } },
	{ id = "Piglet", name = "Piglet", rarity = "Uncommon", powerMul = 0.9, healthMul = 1.15, look = { body = rgb(255, 170, 180), accent = rgb(240, 120, 140), ears = "floppy", tail = "curly" } },
	{ id = "Duckling", name = "Duckling", rarity = "Uncommon", powerMul = 0.95, healthMul = 1.0, look = { body = rgb(255, 240, 120), accent = rgb(255, 140, 30), ears = "none", tail = "short", extra = "beak" } },
	{ id = "Lamb", name = "Lamb", rarity = "Uncommon", powerMul = 0.92, healthMul = 1.12, look = { body = rgb(250, 250, 240), accent = rgb(80, 70, 70), ears = "floppy", tail = "fluffy" } },
	-- Rare
	{ id = "Panda", name = "Panda", rarity = "Rare", powerMul = 0.95, healthMul = 1.15, look = { body = rgb(245, 245, 245), accent = rgb(30, 30, 35), ears = "round", tail = "short", scale = 1.1 } },
	{ id = "Penguin", name = "Penguin", rarity = "Rare", powerMul = 1.0, healthMul = 1.0, look = { body = rgb(35, 40, 55), accent = rgb(250, 250, 250), ears = "none", tail = "short", extra = "beak" } },
	{ id = "Koala", name = "Koala", rarity = "Rare", powerMul = 0.95, healthMul = 1.08, look = { body = rgb(150, 150, 160), accent = rgb(230, 230, 235), ears = "round", tail = "none" } },
	{ id = "Owl", name = "Owl", rarity = "Rare", powerMul = 1.1, healthMul = 0.9, look = { body = rgb(140, 100, 70), accent = rgb(240, 220, 170), ears = "pointy", tail = "short", extra = "beak" } },
	-- Epic
	{ id = "Lion", name = "Lion", rarity = "Epic", powerMul = 1.1, healthMul = 1.0, look = { body = rgb(230, 175, 80), accent = rgb(160, 90, 30), ears = "round", tail = "long", extra = "mane", scale = 1.15 } },
	{ id = "Tiger", name = "Tiger", rarity = "Epic", powerMul = 1.08, healthMul = 0.98, look = { body = rgb(245, 140, 40), accent = rgb(30, 25, 25), ears = "round", tail = "long", extra = "stripes", scale = 1.15 } },
	{ id = "Wolf", name = "Wolf", rarity = "Epic", powerMul = 1.0, healthMul = 1.02, look = { body = rgb(130, 135, 150), accent = rgb(225, 225, 230), ears = "pointy", tail = "fluffy", scale = 1.1 } },
	{ id = "PolarBear", name = "Polar Bear", rarity = "Epic", powerMul = 0.92, healthMul = 1.2, look = { body = rgb(250, 250, 255), accent = rgb(40, 40, 45), ears = "round", tail = "short", scale = 1.25 } },
	-- Legendary (glowing)
	{ id = "GoldenLion", name = "Golden Lion", rarity = "Legendary", powerMul = 1.1, healthMul = 1.0, look = { body = rgb(255, 210, 60), accent = rgb(255, 150, 20), ears = "round", tail = "long", extra = "mane", scale = 1.25 } },
	{ id = "CrystalFox", name = "Crystal Fox", rarity = "Legendary", powerMul = 1.05, healthMul = 0.95, look = { body = rgb(120, 220, 255), accent = rgb(230, 250, 255), ears = "pointy", tail = "fluffy", scale = 1.15 } },
	{ id = "IceWolf", name = "Ice Wolf", rarity = "Legendary", powerMul = 1.0, healthMul = 1.05, look = { body = rgb(190, 235, 255), accent = rgb(80, 160, 255), ears = "pointy", tail = "fluffy", scale = 1.2 } },
	{ id = "RubyPanda", name = "Ruby Panda", rarity = "Legendary", powerMul = 0.92, healthMul = 1.18, look = { body = rgb(255, 90, 110), accent = rgb(110, 20, 40), ears = "round", tail = "short", scale = 1.25 } },
	-- Mythic (rainbow glow)
	{ id = "GalaxyCat", name = "Galaxy Cat", rarity = "Mythic", powerMul = 1.1, healthMul = 0.95, look = { body = rgb(70, 40, 150), accent = rgb(150, 220, 255), ears = "pointy", tail = "long", scale = 1.2 } },
	{ id = "CosmicTiger", name = "Cosmic Tiger", rarity = "Mythic", powerMul = 1.08, healthMul = 1.0, look = { body = rgb(40, 30, 90), accent = rgb(255, 120, 230), ears = "round", tail = "long", extra = "stripes", scale = 1.35 } },
	{ id = "RainbowBunny", name = "Rainbow Bunny", rarity = "Mythic", powerMul = 0.95, healthMul = 1.05, look = { body = rgb(255, 255, 255), accent = rgb(255, 120, 200), ears = "long", tail = "fluffy", scale = 1.2 } },
	{ id = "CelestialDeer", name = "Celestial Deer", rarity = "Mythic", powerMul = 1.0, healthMul = 1.1, look = { body = rgb(255, 235, 200), accent = rgb(255, 215, 90), ears = "pointy", tail = "short", extra = "horn", scale = 1.35 } },
} :: { Animal }

Config.AnimalById = {} :: { [string]: Animal }
Config.AnimalsByRarity = {} :: { [string]: { Animal } }
for _, a in Config.Animals do
	Config.AnimalById[a.id] = a
	local list = Config.AnimalsByRarity[a.rarity]
	if not list then
		list = {}
		Config.AnimalsByRarity[a.rarity] = list
	end
	table.insert(list, a)
end

---------------------------------------------------------------------------
-- The corridor. Run until your stamina runs out; you hatch the egg of the
-- furthest zone you reached. Each zone floor is one Part, so keep every zone
-- shorter than 2048 studs (Roblox's part size limit).
---------------------------------------------------------------------------
-- The run is a wide canyon: checkerboard walls with a grass cap, a checkered
-- floor, voxel props along the walls and the centre left clear for running.
Config.Corridor = {
	width = 140, -- wall to wall
	wallHeight = 80,
	tile = 20, -- checker square size (walls and floor)
	clearHalfWidth = 42, -- no props within this distance of the centre line
	length = 4200, -- total studs; the last zone runs to here
	origin = Vector3.new(0, 0, 40), -- world position of the start line (corridor runs toward +Z)
}

-- One zone per egg of the Voxel Stud Egg Pack. `egg` is the model name in the
-- pack (ReplicatedStorage.EggPack.<egg>); without the pack, eggs are drawn from
-- simple shapes in `eggColor`.
--   floor / floor2: the two checker colours of the floor;  floorMaterial
--   wall / wall2:   the two checker colours of the walls;  cap: the strip on top
--   props:          voxel kit pieces along the walls, { name, weight, tint? }
--   landmark:       one big voxel build at the zone start, seen from far away
Config.Zones = {
	{
		start = 0, name = "Meadow", egg = "GrassEgg", eggName = "Grass Egg", eggColor = rgb(110, 200, 80),
		floor = rgb(95, 200, 70), floor2 = rgb(84, 186, 62), floorMaterial = "Grass",
		wall = rgb(214, 122, 92), wall2 = rgb(199, 109, 82), cap = rgb(90, 190, 70),
		props = { { "VBush", 4 }, { "VBushSmall", 3 }, { "VFlower", 3 }, { "VTree", 2 }, { "VRock", 1, rgb(170, 170, 175) } },
		landmark = "LBigTree",
		weights = { Common = 82, Uncommon = 16, Rare = 2 },
	},
	{
		start = 150, name = "Farm", egg = "SpeckledEgg", eggName = "Speckled Egg", eggColor = rgb(235, 220, 190),
		floor = rgb(150, 200, 90), floor2 = rgb(138, 188, 80), floorMaterial = "Grass",
		wall = rgb(228, 194, 135), wall2 = rgb(214, 180, 122), cap = rgb(90, 190, 70),
		props = { { "VHay", 4 }, { "VBush", 2 }, { "VTree", 2 }, { "VFlower", 2 } },
		landmark = "LBarn",
		weights = { Common = 62, Uncommon = 30, Rare = 7, Epic = 1 },
	},
	{
		start = 350, name = "Hive", egg = "BeeEgg", eggName = "Bee Egg", eggColor = rgb(255, 200, 40),
		floor = rgb(255, 226, 120), floor2 = rgb(245, 212, 106), floorMaterial = "Sand",
		wall = rgb(242, 186, 68), wall2 = rgb(226, 170, 54), cap = rgb(120, 80, 35),
		props = { { "VFlower", 5 }, { "VBushSmall", 3 }, { "VBush", 2 } },
		landmark = "LBeehive",
		weights = { Common = 42, Uncommon = 36, Rare = 17, Epic = 5 },
	},
	{
		start = 600, name = "Beach", egg = "OceanEgg", eggName = "Ocean Egg", eggColor = rgb(60, 160, 230),
		floor = rgb(246, 226, 168), floor2 = rgb(236, 214, 154), floorMaterial = "Sand",
		wall = rgb(92, 178, 232), wall2 = rgb(78, 164, 222), cap = rgb(246, 226, 168),
		props = { { "VPalm", 4 }, { "VRock", 2, rgb(225, 205, 160) }, { "VBushSmall", 1 } },
		landmark = "LRainbow",
		weights = { Common = 25, Uncommon = 38, Rare = 27, Epic = 9, Legendary = 1 },
	},
	{
		start = 950, name = "Snow", egg = "FrostEgg", eggName = "Frost Egg", eggColor = rgb(200, 235, 255),
		floor = rgb(240, 248, 255), floor2 = rgb(226, 238, 250), floorMaterial = "Snow",
		wall = rgb(176, 214, 246), wall2 = rgb(160, 200, 236), cap = rgb(255, 255, 255),
		props = { { "VPine", 4 }, { "VIce", 2, rgb(150, 210, 255) }, { "VRock", 1, rgb(235, 240, 250) } },
		landmark = "LSnowman",
		weights = { Common = 12, Uncommon = 32, Rare = 35, Epic = 17, Legendary = 3.5, Mythic = 0.5 },
	},
	{
		start = 1400, name = "Volcano", egg = "LavaEgg", eggName = "Lava Egg", eggColor = rgb(255, 90, 30),
		floor = rgb(78, 64, 62), floor2 = rgb(66, 54, 52), floorMaterial = "Basalt",
		wall = rgb(112, 62, 52), wall2 = rgb(98, 52, 44), cap = rgb(255, 110, 30),
		props = { { "VLavaRock", 4 }, { "VRock", 2, rgb(80, 70, 70) } },
		landmark = "LVolcano",
		weights = { Uncommon = 22, Rare = 40, Epic = 28, Legendary = 8.5, Mythic = 1.5 },
	},
	{
		start = 2000, name = "Storm", egg = "StormEgg", eggName = "Storm Egg", eggColor = rgb(120, 110, 200),
		floor = rgb(126, 126, 150), floor2 = rgb(114, 114, 138), floorMaterial = "Slate",
		wall = rgb(112, 102, 156), wall2 = rgb(100, 90, 142), cap = rgb(70, 62, 104),
		props = { { "VRock", 3, rgb(120, 120, 140) }, { "VPine", 2 }, { "VCloud", 2 } },
		landmark = "LStormCloud",
		weights = { Uncommon = 8, Rare = 35, Epic = 38, Legendary = 15, Mythic = 4 },
	},
	{
		start = 2700, name = "Crystal", egg = "CrystalEgg", eggName = "Crystal Egg", eggColor = rgb(170, 120, 255),
		floor = rgb(204, 184, 246), floor2 = rgb(192, 170, 236), floorMaterial = "SmoothPlastic",
		wall = rgb(170, 130, 232), wall2 = rgb(156, 116, 220), cap = rgb(120, 230, 255),
		props = { { "VCrystal", 4, rgb(150, 110, 255) }, { "VCrystal", 3, rgb(110, 220, 255) }, { "VRock", 1, rgb(190, 170, 235) } },
		landmark = "LBigCrystal",
		weights = { Rare = 24, Epic = 44, Legendary = 25, Mythic = 7 },
	},
	{
		start = 3500, name = "Golden", egg = "GoldenEgg", eggName = "Golden Egg", eggColor = rgb(255, 205, 50),
		floor = rgb(255, 236, 172), floor2 = rgb(246, 224, 156), floorMaterial = "SmoothPlastic",
		wall = rgb(242, 200, 82), wall2 = rgb(228, 186, 66), cap = rgb(255, 250, 235),
		props = { { "VPillar", 3 }, { "VCrystal", 2, rgb(255, 205, 60) } },
		landmark = "LPyramid",
		weights = { Epic = 40, Legendary = 45, Mythic = 15 },
	},
} :: { Zone }

-- Egg display data, keyed by egg id (= the pack's model name).
Config.Eggs = {} :: { [string]: { id: string, name: string, zone: number, color: Color3 } }
for i, z in Config.Zones do
	Config.Eggs[z.egg] = { id = z.egg, name = z.eggName, zone = i, color = z.eggColor }
end

-- Where the game looks for the Voxel Stud Egg Pack models (first match wins).
-- Copy the pack's "EggPack" folder into ReplicatedStorage (see README).
Config.EggPackFolder = "EggPack"

---------------------------------------------------------------------------
-- Upgrades bought with Coins. cost(level) = base * growth ^ level, where
-- level is the CURRENT level (the cost of going to level + 1).
---------------------------------------------------------------------------
Config.Upgrades = {
	Speed = { name = "Speed", base = 40, growth = 1.32, max = 30, start = 16, step = 2, unit = "speed" },
	Stamina = { name = "Stamina", base = 50, growth = 1.36, max = 40, start = 8, step = 1.5, unit = "s" },
	Training = { name = "Training", base = 80, growth = 1.45, max = 25, start = 2, step = 1, unit = "XP/s" },
}
Config.UpgradeOrder = { "Speed", "Stamina", "Training" }
Config.MaxWalkSpeed = 120 -- hard cap after upgrades and team bonuses

---------------------------------------------------------------------------
-- Animals: levels, team, inventory.
---------------------------------------------------------------------------
Config.Pets = {
	teamSize = 3,
	maxOwned = 60,
	maxLevel = 50,
	powerPerLevel = 0.12, -- +12% power per level above 1
	healthPerLevel = 0.10,
	rollMin = 0.9, -- each hatched animal gets a random quality roll
	rollMax = 1.1,
	xpBase = 15, -- xp to next level = floor(xpBase * level ^ xpExponent)
	xpExponent = 1.6,
}

---------------------------------------------------------------------------
-- Training pad on each plot: team animals gain XP while you stand on it.
---------------------------------------------------------------------------
Config.Training = {
	padRadius = 9,
	tickSeconds = 1,
}

---------------------------------------------------------------------------
-- Arena: NPC waves. Level L enemy fighter: power = basePower * growth^(L-1).
---------------------------------------------------------------------------
Config.Arena = {
	basePower = 8,
	powerGrowth = 1.2,
	healthPerPower = 6,
	rewardBase = 25,
	rewardGrowth = 1.17,
	xpBase = 6, -- xp to each of your fighters on a win: xpBase + xpPerLevel * L
	xpPerLevel = 2,
	maxRounds = 25,
	critChance = 0.12,
	critMultiplier = 1.6,
	secondsPerHit = 0.55, -- client playback speed; the server also waits this long between fights
	-- team size by level
	teamSizes = { { from = 1, size = 1 }, { from = 5, size = 2 }, { from = 15, size = 3 } },
}

---------------------------------------------------------------------------
-- World layout (studs). The map is generated by MapBuilder from these.
---------------------------------------------------------------------------
Config.World = {
	hubSize = Vector3.new(220, 1, 120), -- hub platform centred at (0, 0, -20)
	plotCount = 6,
	plotSize = 56,
	plotRow = -130, -- Z of the plot row centre
	plotSpacing = 64,
	arenaCenter = Vector3.new(0, 0, -232),
	arenaSize = 70,
}

return Config
