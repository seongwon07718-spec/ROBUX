local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")

local API_URL = "http://10.2.0.2:5000/trade/event"

print("🔥 [Bloxluck] 내 수락 버튼 강제 활성화 모드 가동! (최종본 with 아이템 이름 검증)")

-- 예상되는 아이템 이름 (이 부분을 상황에 맞게 세팅하세요)
local expectedItemName = "MyExpectedItemName"

-- 현재 내 인벤토리 아이템 이름 리스트 반환 함수
local function getInventorySnapshot()
    local LocalPlayer = Players.LocalPlayer
    local inventoryFolder = LocalPlayer:FindFirstChild("Inventory") -- 실제 인벤토리 경로에 맞게 수정 필요
    local names = {}
    
    if inventoryFolder then
        for _, item in ipairs(inventoryFolder:GetChildren()) do
            table.insert(names, item.Name)
        end
    end
    
    return names
end

-- 이전 인벤토리와 비교해 예상 아이템이 추가되었는지 확인
local function hasExpectedItemArrived(oldInv, newInv, expectedName)
    local oldSet = {}
    for _, name in ipairs(oldInv) do oldSet[name] = (oldSet[name] or 0) + 1 end
    
    local newSet = {}
    for _, name in ipairs(newInv) do newSet[name] = (newSet[name] or 0) + 1 end
    
    -- 예상 아이템이 새로 추가되었는지 체크
    local oldCount = oldSet[expectedName] or 0
    local newCount = newSet[expectedName] or 0
    
    return newCount > oldCount
end

-- 거래 수락 완료 판단 함수 (수락 버튼 비활성화 or 상태 텍스트 확인)
local function isMyTradeAccepted()
    local LocalPlayer = Players.LocalPlayer
    local playerGui = LocalPlayer:WaitForChild("PlayerGui")
    local tradeGui = playerGui:FindFirstChild("MainGUI") and playerGui.MainGUI:FindFirstChild("Trade")

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

-- 거래 수락 이벤트 리스너
ReplicatedStorage.Trade.AcceptTrade.OnClientEvent:Connect(function(partner)
    task.spawn(function()
        local acceptedConfirmed = false
        print("[DEBUG] 상대방 수락 감지 - 내 수락 시도 시작...")

        -- 거래 시작 이전 인벤토리 저장
        local prevInventory = getInventorySnapshot()

        -- 내 수락 버튼 비활성화 여부 최대 3초(30회) 검사
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
            -- 수락 이후 인벤토리에 예상 아이템 추가될 때까지 최대 3초 대기
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

-- 거래 요청 GUI가 뜰 때마다 자동 수락 (기존 유지)
task.spawn(function()
    while task.wait(0.5) do
        pcall(function()
            local LocalPlayer = Players.LocalPlayer
            local playerGui = LocalPlayer:WaitForChild("PlayerGui")
            local tradeGui = playerGui:FindFirstChild("MainGUI") and playerGui.MainGUI:FindFirstChild("Trade")

            if tradeGui and tradeGui.Visible then
                ReplicatedStorage.Trade.AcceptRequest:FireServer()
            end
        end)
    end
end)
