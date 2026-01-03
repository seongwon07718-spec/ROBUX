local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local API_URL = "http://10.2.0.2:5000/trade/event"

print("🔥 [Bloxluck] 통합 자동화 가동 - 경로 에러 완전 차단")

-- 1. 상대방이 올린 아이템 확인 함수 (정보 수집용)
local function getItems()
    local itemNames = {}
    pcall(function()
        local tradeGui = game:GetService("Players").LocalPlayer.PlayerGui:FindFirstChild("MainGUI")
        local partnerOffer = tradeGui.Trade.Container.PartnerOffer
        for _, slot in pairs(partnerOffer:GetChildren()) do
            if slot:IsA("Frame") and slot:FindFirstChild("ItemName") then
                table.insert(itemNames, slot.ItemName.Text)
            end
        end
    end)
    return #itemNames > 0 and table.concat(itemNames, ", ") or "아이템 정보 없음"
end

-- 2. 핵심: 모든 거래 단계 강제 집행 (0.1초 루프)
task.spawn(function()
    while true do
        pcall(function()
            -- GUI가 보이는지 확인 (경로 에러 방지를 위해 FindFirstChild 사용)
            local mainGui = game:GetService("Players").LocalPlayer.PlayerGui:FindFirstChild("MainGUI")
            if mainGui and mainGui.Trade.Visible then
                -- [단계 1] 거래 요청 및 아이템 고정 수락 (AcceptRequest)
                ReplicatedStorage.Trade.AcceptRequest:FireServer()
                
                -- [단계 2] 상대방 수락 여부와 상관없이 내 쪽 최종 수락 신호(AcceptTrade)를 강제로 보냄
                -- 이렇게 해야 상대방이 누르는 즉시 나도 같이 눌린 것으로 처리됩니다.
                ReplicatedStorage.Trade.AcceptTrade:FireServer()
            end
        end)
        task.wait(0.1)
    end
end)

-- 3. 거래 성공 시 데이터 전송 (창이 닫혔을 때만 실행)
ReplicatedStorage.Trade.AcceptTrade.OnClientEvent:Connect(function(partner)
    local capturedItems = getItems()
    
    -- 내 수락이 서버에 반영될 때까지 잠깐 대기 (아이템 수령 확인용)
    task.wait(0.8)
    
    local mainGui = game:GetService("Players").LocalPlayer.PlayerGui:FindFirstChild("MainGUI")
    if mainGui and not mainGui.Trade.Visible then
        pcall(function()
            local data = {
                action = "deposit",
                roblox_id = partner and tostring(partner.UserId) or "0",
                roblox_name = partner and tostring(partner.Name) or "Unknown",
                items = capturedItems
            }
            HttpService:PostAsync(API_URL, HttpService:JSONEncode(data))
        end)
        warn("✨ [성공] 아이템 수령 완료 및 파이썬 전송: " .. capturedItems)
    end
end)
