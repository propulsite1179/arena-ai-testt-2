--!strict
-- ORIGINAL BENCHMARK STARTER, NOT A COMPLETED MODEL OUTPUT.
-- Run only in Edit mode in an explicitly consented disposable project copy.
-- Does not publish, upload assets, call external services, or touch other roots.
local Workspace = game:GetService("Workspace")
local name = "GDB_rbx_remote_security"
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
module("PurchaseAuthority", [==[
-- INTENTIONALLY INSECURE TEST INPUT. NEVER USE THIS IMPLEMENTATION IN A LIVE GAME.
-- Repair task: client claims must not define item price, quantity bounds, or identity.
local Authority = {}
function Authority.purchase(account, request, catalog, _now)
    account.coins -= request.price
    account.items[request.item] = (account.items[request.item] or 0) + request.quantity
    return true
end
return Authority
]==])
module("ContractTests", [==[
return function(Authority)
    local account = {coins = 20, items = {}, lastPurchaseAt = -100}
    local catalog = {gem = {price = 5, maxQuantity = 3}}
    assert(not Authority.purchase(account, {item = "gem", price = -1000, quantity = -1}, catalog, 10))
    assert(account.coins == 20, "invalid request changed balance")
    assert(not Authority.purchase(account, {item = "missing", quantity = 1}, catalog, 20))
    assert(not Authority.purchase(account, "malformed", catalog, 30))
    assert(Authority.purchase(account, {item = "gem", quantity = 2}, catalog, 40))
    assert(account.coins == 10 and account.items.gem == 2, "server catalog must determine the price")
    assert(not Authority.purchase(account, {item = "gem", quantity = 1}, catalog, 40.01), "rate limit")
    return {pureAssertions = 7, requiresRemoteIdentityPlaytest = true}
end
]==])

return root:GetFullName()
