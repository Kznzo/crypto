--!strict
-- Egg Run: where everything is. Pure maths from Config, shared by the map
-- builder, the server services and the client, so they always agree.
-- Install: ReplicatedStorage/EggRun/Layout (ModuleScript)
--
-- World plan ("Hatch Plaza"):
--   spawn plaza at the centre, main aisle runs +Z to the START arch (z = 40)
--   3 bases on each side of the aisle, each facing it
--   the corridor runs from the START arch toward +Z, 9 themed zones
--   the Battle Box arena sits behind the plaza (-Z)

local Config = require(script.Parent:WaitForChild("Config"))

local Layout = {}

Layout.GroundY = 0 -- top surface of every walkable floor

-- Plaza / hub
Layout.Spawn = CFrame.lookAt(Vector3.new(0, 0.5, -70), Vector3.new(0, 0.5, 40))
Layout.AisleHalfWidth = 16
Layout.HubMin = Vector3.new(-230, 0, -280)
Layout.HubMax = Vector3.new(230, 0, 40)

-- Corridor
local origin = Config.Corridor.origin
Layout.CorridorStartZ = origin.Z
Layout.CorridorEndZ = origin.Z + Config.Corridor.length
Layout.LaneHalfWidth = Config.Corridor.width / 2
Layout.BedWidth = 16 -- decorated side beds beyond the lane edges

function Layout.ZoneRange(index: number): (number, number)
	local zones = Config.Zones
	local startZ = origin.Z + zones[index].start
	local endZ = if index < #zones then origin.Z + zones[index + 1].start else Layout.CorridorEndZ
	return startZ, endZ
end

-- Distance (studs from the start line) for a world Z position, clamped at 0.
function Layout.DistanceAt(worldZ: number): number
	return math.max(0, worldZ - origin.Z)
end

-- True when a world position is inside the running lane (with a small margin).
function Layout.InLane(position: Vector3): boolean
	return position.Z >= origin.Z
		and position.Z <= Layout.CorridorEndZ
		and math.abs(position.X - origin.X) <= Layout.LaneHalfWidth + 2
		and position.Y > -20
		and position.Y < 60
end

---------------------------------------------------------------------------
-- Bases (plots). Index 1-3 on the left (-X), 4-6 on the right (+X).
-- Each plot's CFrame sits at its floor centre with LookVector toward the aisle,
-- so "front" is local -Z.
---------------------------------------------------------------------------
Layout.PlotSize = Config.World.plotSize
local PLOT_X = 104
local PLOT_ROW_Z = { -150, -82, -14 }

Layout.PlotColors = {
	Color3.fromRGB(150, 220, 170), -- mint
	Color3.fromRGB(140, 200, 245), -- sky
	Color3.fromRGB(255, 190, 150), -- peach
	Color3.fromRGB(200, 170, 240), -- lilac
	Color3.fromRGB(255, 230, 130), -- lemon
	Color3.fromRGB(255, 160, 170), -- coral
}

function Layout.PlotCFrame(index: number): CFrame
	assert(index >= 1 and index <= Config.World.plotCount, `Layout: no plot {index}`)
	local side = if index <= 3 then -1 else 1
	local row = (index - 1) % 3 + 1
	local center = Vector3.new(side * PLOT_X, Layout.GroundY, PLOT_ROW_Z[row])
	return CFrame.lookAt(center, center + Vector3.new(-side, 0, 0))
end

-- Where a player appears at their base: near the front, facing the aisle.
function Layout.PlotSpawn(index: number): CFrame
	return Layout.PlotCFrame(index) * CFrame.new(0, 3.5, -Layout.PlotSize / 2 + 9)
end

-- Training pad centre (on the floor).
function Layout.PlotPad(index: number): Vector3
	return (Layout.PlotCFrame(index) * CFrame.new(0, 0, 4)).Position
end

-- Three podiums at the back of the base that show the player's team.
function Layout.PlotPodiums(index: number): { CFrame }
	local cf = Layout.PlotCFrame(index)
	local list = {}
	for i, x in { -12, 0, 12 } do
		list[i] = cf * CFrame.new(x, 0, Layout.PlotSize / 2 - 9)
	end
	return list
end

---------------------------------------------------------------------------
-- Arena ("Battle Box")
---------------------------------------------------------------------------
local arena = Config.World.arenaCenter
Layout.ArenaCenter = Vector3.new(arena.X, Layout.GroundY, -232)
Layout.ArenaSize = Config.World.arenaSize

function Layout.ArenaSlots(side: number, count: number): { CFrame }
	-- side 1 = the player's team (near the entrance, +Z), side 2 = enemies
	local z = if side == 1 then 14 else -14
	local face = if side == 1 then -1 else 1
	local list = {}
	for i = 1, count do
		local x = (i - (count + 1) / 2) * 12
		local pos = Layout.ArenaCenter + Vector3.new(x, 0, z)
		list[i] = CFrame.lookAt(pos, pos + Vector3.new(0, 0, face))
	end
	return list
end

-- Where the player's character waits during a fight (on the viewing deck).
Layout.ArenaViewer = CFrame.lookAt(
	Layout.ArenaCenter + Vector3.new(0, 7.5, Layout.ArenaSize / 2 + 10),
	Layout.ArenaCenter + Vector3.new(0, 7.5, 0)
)

-- Camera used by the client while a fight plays.
Layout.ArenaCamera = CFrame.lookAt(
	Layout.ArenaCenter + Vector3.new(0, 34, 58),
	Layout.ArenaCenter + Vector3.new(0, 2, 0)
)

return Layout
