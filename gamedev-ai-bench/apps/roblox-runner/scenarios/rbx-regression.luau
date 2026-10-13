--!strict
-- ORIGINAL BENCHMARK STARTER, NOT A COMPLETED MODEL OUTPUT.
-- Run only in Edit mode in an explicitly consented disposable project copy.
-- Does not publish, upload assets, call external services, or touch other roots.
local Workspace = game:GetService("Workspace")
local name = "GDB_rbx_regression"
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
part("RegressionFloor", Vector3.new(0, 0, 0), Vector3.new(60, 1, 60))
module("MovementConfig", [==[
return {walkSpeed = 16, jumpHeight = 7.2, sprintSpeed = 24, sprintCooldown = 2}
]==])
module("ExistingContract", [==[
return function(config)
    assert(config.walkSpeed == 16, "existing walk behavior must remain unchanged")
    assert(config.jumpHeight == 7.2, "existing jump behavior must remain unchanged")
    assert(config.sprintCooldown >= 2)
    return {pureAssertions = 3, requiresRespawnAndSprintPlaytest = true}
end
]==])
-- Candidate adds bounded sprint with cooldown without changing existing walk/jump APIs.

return root:GetFullName()
