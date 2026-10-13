--!strict
-- ORIGINAL BENCHMARK STARTER, NOT A COMPLETED MODEL OUTPUT.
-- Run only in Edit mode in an explicitly consented disposable project copy.
-- Does not publish, upload assets, call external services, or touch other roots.
local Workspace = game:GetService("Workspace")
local name = "GDB_rbx_multiplayer"
assert(not Workspace:FindFirstChild(name), "Starter already exists; use a fresh project copy")
local root = Instance.new("Folder")
root.Name = name
root.Parent = Workspace
local function part(label: string, position: Vector3, size: Vector3): Part
    local p = Instance.new("Part")
    p.Name = label; p.Anchored = true; p.Position = position; p.Size = size
    p.Color = Color3.fromRGB(90, 210, 165); p.Parent = root
    return p
end
local function module(label: string, source: string): ModuleScript
    local m = Instance.new("ModuleScript"); m.Name = label; m.Source = source; m.Parent = root
    return m
end
part("ArenaFloor", Vector3.new(0, 0, 0), Vector3.new(50, 1, 50))
module("RoundState", [==[
-- Deliberately flawed: each client call advances the shared round independently.
local RoundState = {round = 0, phase = "waiting"}
function RoundState.start(_caller, _eligible)
    RoundState.round += 1
    RoundState.phase = "running"
    return RoundState.round
end
return RoundState
]==])
-- Candidate must enforce server-only transitions, one start per round, and late-join snapshots.
-- Requires at least two real Studio clients. A single-player playtest is insufficient evidence.
root:SetAttribute("RequiredClients", 2)

return root:GetFullName()
