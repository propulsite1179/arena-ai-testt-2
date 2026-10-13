--!strict
-- ORIGINAL BENCHMARK STARTER, NOT A COMPLETED MODEL OUTPUT.
-- Run only in Edit mode in an explicitly consented disposable project copy.
-- Does not publish, upload assets, call external services, or touch other roots.
local Workspace = game:GetService("Workspace")
local name = "GDB_rbx_rewards"
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
module("Rewards", [==[
local Rewards = {}
function Rewards.claim(_state, _eventId: string, _eligible: boolean): boolean
    error("Candidate must implement idempotent, eligibility-checked reward claims")
end
return Rewards
]==])
module("ContractTests", [==[
return function(Rewards)
    local state = {coins = 0, claimed = {}}
    assert(not Rewards.claim(state, "round-1", false))
    assert(state.coins == 0)
    assert(Rewards.claim(state, "round-1", true))
    assert(state.coins == 10)
    assert(not Rewards.claim(state, "round-1", true))
    assert(state.coins == 10, "repeat event must not duplicate reward")
    assert(Rewards.claim(state, "round-2", true) and state.coins == 20)
    return {pureAssertions = 7, requiresReconnectPlaytest = true}
end
]==])

return root:GetFullName()
