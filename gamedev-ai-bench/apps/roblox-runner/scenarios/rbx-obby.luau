--!strict
-- ORIGINAL BENCHMARK STARTER, NOT A COMPLETED MODEL OUTPUT.
-- Run only in Edit mode in an explicitly consented disposable project copy.
-- Does not publish, upload assets, call external services, or touch other roots.
local Workspace = game:GetService("Workspace")
local name = "GDB_rbx_obby"
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
part("SpawnFloor", Vector3.new(0, 0, 0), Vector3.new(18, 1, 18))
local spawn = Instance.new("SpawnLocation"); spawn.Name = "Start"; spawn.Anchored = true
spawn.Position = Vector3.new(0, 2, 0); spawn.Size = Vector3.new(5, 1, 5); spawn.Parent = root
-- Candidate must build an original playable course and server-owned checkpoints.
root:SetAttribute("RequiredCheckpoints", 5)
root:SetAttribute("MaximumParts", 120)

return root:GetFullName()
