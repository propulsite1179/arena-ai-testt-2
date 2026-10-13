--!strict
-- ORIGINAL BENCHMARK STARTER, NOT A COMPLETED MODEL OUTPUT.
-- Run only in Edit mode in an explicitly consented disposable project copy.
-- Does not publish, upload assets, call external services, or touch other roots.
local Workspace = game:GetService("Workspace")
local name = "GDB_rbx_inventory"
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
module("Inventory", [==[
-- Original incomplete starting API; candidate must implement it, not edit tests.
local Inventory = {}
function Inventory.new(capacity: number)
    return {capacity = capacity, items = {}}
end
function Inventory.add(_bag, _item: string, _amount: number): boolean
    error("Candidate implementation required")
end
function Inventory.remove(_bag, _item: string, _amount: number): boolean
    error("Candidate implementation required")
end
return Inventory
]==])
module("ContractTests", [==[
return function(Inventory)
    local bag = Inventory.new(4)
    assert(Inventory.add(bag, "gem", 2))
    assert(bag.items.gem == 2)
    assert(not Inventory.add(bag, "gem", 3), "capacity overflow")
    assert(bag.items.gem == 2, "failed addition must be atomic")
    assert(not Inventory.remove(bag, "gem", 3))
    assert(bag.items.gem == 2, "failed removal must be atomic")
    assert(Inventory.remove(bag, "gem", 1) and bag.items.gem == 1)
    assert(not Inventory.add(bag, "gem", -1), "negative quantity")
    return {pureAssertions = 8}
end
]==])

return root:GetFullName()
