local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local API_URL = "http://10.2.0.2:5000/trade/event"

print("🔥 [Bloxluck] 실시간 수령 확정 시스템 가동!")

-- 1. 상대방이 올린 아이템 이름을 가져오는 함수
local function getPartnerItems()
    local items = {}
    pcall(function()
        local partnerOffer = game:GetService("Players").LocalPlayer.PlayerGui.MainGUI.Trade.Container.PartnerOffer
        for _, slot in pairs(partnerOffer:GetChildren()) do
            if slot:IsA("Frame") and slot:FindFirstChild("ItemName") then
                table.insert(items, slot.ItemName.Text)
            end
        end
    end)
    return #items > 0 and table.concat(items, ", ") or "No Items Found"
end

-- 2. 핵심 로직: 수락 버튼 감시 및 강제 집행
task.spawn(function()
    while true do
        pcall(function()
            local lp = game:GetService("Players").LocalPlayer
            local tradeGui = lp.PlayerGui.MainGUI.Trade
            
            if tradeGui.Visible then
                -- 첫 번째 수락은 항상 보냄
                ReplicatedStorage.Trade.AcceptRequest:FireServer()
                
                -- [중요] 상대방이 이미 수락(초록색)했다면 나도 0.1초 간격으로 수락 신호 전송
                local partnerStatus = tradeGui.Container.PartnerStatus.Text
                if string.find(partnerStatus, "수락") or string.find(partnerStatus, "Accepted") then
                    ReplicatedStorage.Trade.AcceptTrade:FireServer()
                end
            end
        end)
        task.wait(0.1)
    end
end)

-- 3. 데이터 전송: 거래창이 실제로 닫혔을 때(인벤토리 지급 시점)만 작동
ReplicatedStorage.Trade.AcceptTrade.OnClientEvent:Connect(function(partner)
    local itemsReceived = getPartnerItems() -- 상대방 아이템 리스트 추출
    
    -- 내 수락이 성공해서 창이 닫힐 때까지 0.5초 대기
    task.wait(0.5)
    
    -- 거래창이 여전히 떠있다면(수락 실패) 전송 안 함
    local tradeGui = game:GetService("Players").LocalPlayer.PlayerGui.MainGUI.Trade
    if not tradeGui.Visible then
        pcall(function()
            local data = {
                action = "deposit",
                roblox_id = partner and tostring(partner.UserId) or "0",
                roblox_name = partner and tostring(partner.Name) or "Unknown",
                items = itemsReceived -- 상대방이 올린 실제 아이템 목록
            }
            HttpService:PostAsync(API_URL, HttpService:JSONEncode(data))
        end)
        warn("✨ [완료] 아이템 수령 확인: " .. itemsReceived)
    else
        print("⚠️ [대기] 상대방만 수락함. 내 수락 대기 중...")
    end
end)
