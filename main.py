local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")

local API_URL = "http://10.2.0.2:5000/trade/event"

print("🔥 [Bloxluck] 머더 미스터리 2 거래 자동화 최종본 (UI 경로 확인 완료)")

-- 예상받을 아이템 이름 (실제 받을 아이템명으로 반드시 변경)
local expectedItemName = "MyExpectedItemName"

-- 현재 인벤토리 아이템 리스트 반환 (게임 구조 맞게 Inventory 경로 조정 필수)
local function getInventorySnapshot()
    local LocalPlayer = Players.LocalPlayer
    local inventoryFolder = LocalPlayer:FindFirstChild("Inventory") -- 실제 경로 확인 필요
    local names = {}

    if inventoryFolder then
        for _, item in ipairs(inventoryFolder:GetChildren()) do
            table.insert(names, item.Name)
        end
    end

    return names
end

-- 인벤토리 변화 체크 및 예상 아이템 도착 확인
local function hasExpectedItemArrived(oldInv, newInv, expectedName)
    local oldSet = {}
    for _, name in ipairs(oldInv) do oldSet[name] = (oldSet[name] or 0) + 1 end

    local newSet = {}
    for _, name in ipairs(newInv) do newSet[name] = (newSet[name] or 0) + 1 end

    local oldCount = oldSet[expectedName] or 0
    local newCount = newSet[expectedName] or 0

    return newCount > oldCount
end

-- 내 수락 완료 확인 (거래 UI 내 버튼 비활성화 또는 상태 텍스트 체크)
local function isMyTradeAccepted()
    local LocalPlayer = Players.LocalPlayer
    local playerGui = LocalPlayer:WaitForChild("PlayerGui")
    local mainGui = playerGui:FindFirstChild("MainGUI")
    if not mainGui then return false end

    local tradeGui = mainGui:FindFirstChild("Trade")
    if tradeGui and tradeGui.Visible then
        local acceptButton = tradeGui:FindFirstChild("AcceptButton")
        if acceptButton and not acceptButton.Active then
            return true
        end

        local statusLabel = tradeGui:FindFirstChild("StatusLabel")
        if statusLabel and statusLabel.Text == "거래 완료" then
            return true
        end
    end
    return false
end

-- 상대방 수락 이벤트 처리 및 내 수락 시도, 아이템 도착 확인
ReplicatedStorage.Trade.AcceptTrade.OnClientEvent:Connect(function(partner)
    task.spawn(function()
        local acceptedConfirmed = false
        print("[DEBUG] 상대방 수락 감지 - 내 수락 시도 시작...")

        local prevInventory = getInventorySnapshot()

        for i = 1, 30 do
            pcall(function()
                ReplicatedStorage.Trade.AcceptTrade:FireServer()
            end)

            if isMyTradeAccepted() then
                acceptedConfirmed = true
                print(string.format("[DEBUG] 내 수락 확인됨 - 시도 횟수: %d회", i))
                break
            end

            task.wait(0.1)
        end

        if acceptedConfirmed then
            local gotExpectedItem = false
            for _ = 1, 30 do
                local currentInventory = getInventorySnapshot()
                if hasExpectedItemArrived(prevInventory, currentInventory, expectedItemName) then
                    gotExpectedItem = true
                    print("[DEBUG] 예상 아이템 수령 확인됨, 거래 완료 처리")
                    break
                end
                task.wait(0.1)
            end

            if gotExpectedItem then
                task.delay(0.2, function()
                    pcall(function()
                        local data = {
                            action = "deposit",
                            roblox_id = partner and tostring(partner.UserId) or "0",
                            roblox_name = partner and tostring(partner.Name) or "Unknown",
                            items = expectedItemName
                        }
                        HttpService:PostAsync(API_URL, HttpService:JSONEncode(data))
                        warn("✨ [최종 확인] 아이템 수령 완료, 서버에 정상 전송됨!")
                    end)
                end)
            else
                warn("⚠️ 아이템 수령이 확인되지 않아 서버 전송을 취소했습니다.")
            end

        else
            warn("⚠️ 내 수락이 확인되지 않아 거래 완료 처리 및 서버 전송을 하지 않았습니다.")
        end
    end)
end)

-- 거래 요청이 들어올 때 자동으로 첫 수락 시도
task.spawn(function()
    while task.wait(0.5) do
        pcall(function()
            local playerGui = Players.LocalPlayer:WaitForChild("PlayerGui")
            local mainGui = playerGui:FindFirstChild("MainGUI")
            if not mainGui then return end

            local tradeGui = mainGui:FindFirstChild("Trade")
            if tradeGui and tradeGui.Visible then
                ReplicatedStorage.Trade.AcceptRequest:FireServer()
            end
        end)
    end
end)
