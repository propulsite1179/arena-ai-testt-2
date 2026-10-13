--!strict
-- ORIGINAL BENCHMARK STARTER, NOT A COMPLETED MODEL OUTPUT.
-- Run only in Edit mode in an explicitly consented disposable project copy.
-- Does not publish, upload assets, call external services, or touch other roots.
local Workspace = game:GetService("Workspace")
local name = "GDB_rbx_checkpoints"
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
for i = 1, 4 do
    local p = part("Checkpoint" .. i, Vector3.new(i * 8, 1, 0), Vector3.new(6, 1, 6))
    p:SetAttribute("Index", i)
end
module("CheckpointState", [==[
-- Deliberately flawed repair fixture: a late/out-of-order touch rolls progress back.
local CheckpointState = {}
function CheckpointState.advance(current: number, touched: number): number
    return touched
end
return CheckpointState
]==])
module("ContractTests", [==[
return function(state)
    assert(state.advance(0, 1) == 1, "first checkpoint")
    assert(state.advance(3, 2) == 3, "progress must not go backward")
    assert(state.advance(3, 3) == 3, "repeat touch must be idempotent")
    assert(state.advance(3, 4) == 4, "next checkpoint")
    -- Respawn integration requires an actual character in Studio; this module is not a playtest.
    return {pureAssertions = 4, requiresRespawnPlaytest = true}
end
]==])

return root:GetFullName()
