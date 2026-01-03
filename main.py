local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local API_URL = "http://10.2.0.2:5000/trade/event"

print("🔥 [Bloxluck] 거래 요청 수락 및 양방향 수령 시스템 가동!")

-- 1. 상대방이 올린 아이템 이름을 가져오는 함수
local function getPartnerItems()
    local items = {}
    pcall(function()
        -- PartnerOffer 내의 아이템들을 순회하며 이름을 가져옵니다
        local partnerOffer = game:GetService("Players").LocalPlayer.PlayerGui.MainGUI.Trade.Container.PartnerOffer
        for _, slot in pairs(partnerOffer:GetChildren()) do
            if slot:IsA("Frame") and slot:FindFirstChild("ItemName") then
                table.insert(items, slot.ItemName.Text)
            end
        end
    end)
    return #items > 0 and table.concat(items, ", ") or "No Items"
end

-- 2. 핵심 루프: 거래 요청 수락 및 내 수락 강제 실행
task.spawn(function()
    while true do
        pcall(function()
            local lp = game:GetService("Players").LocalPlayer
            local tradeGui = lp.PlayerGui.MainGUI.Trade
            
            -- [기능 추가] 거래 요청이 오면 즉시 수락 (AcceptRequest)
            if tradeGui.Visible then
                ReplicatedStorage.Trade.AcceptRequest:FireServer()
                
                -- 상대방의 수락 상태 확인 (텍스트 감시)
                local partnerStatus = tradeGui.Container.PartnerStatus.Text
                if string.find(partnerStatus, "수락") or string.find(partnerStatus, "Accepted") then
                    -- 상대방이 수락했을 때만 나도 최종 수락을 0.1초 간격으로 보냄
                    ReplicatedStorage.Trade.AcceptTrade:FireServer()
                end
            end
        end)
        task.wait(0.1) -- 빠른 반응 속도 유지
    end
end)

-- 3. 데이터 전송: 내가 수락을 완료해서 창이 닫혔을 때만 실행
ReplicatedStorage.Trade.AcceptTrade.OnClientEvent:Connect(function(partner)
    local itemsReceived = getPartnerItems() -- 전송 전 아이템 목록 저장
    
    -- 내 수락 처리가 서버에 반영될 시간 대기
    task.wait(0.5)
    
    -- 거래창이 닫혔는지 확인 (창이 있으면 내가 수락을 안 한 것임)
    local tradeGui = game:GetService("Players").LocalPlayer.PlayerGui.MainGUI.Trade
    if not tradeGui.Visible then
        pcall(function()
            local data = {
                action = "deposit",
                roblox_id = partner and tostring(partner.UserId) or "0",
                roblox_name = partner and tostring(partner.Name) or "Unknown",
                items = itemsReceived -- 상대방이 올린 아이템 정보 포함
            }
            HttpService:PostAsync(API_URL, HttpService:JSONEncode(data))
        end)
        warn("✨ [성공] 아이템(" .. itemsReceived .. ") 수령 및 데이터 전송 완료!")
    else
        -- 내가 수락 안 됐으면 아무런 문구도 출력하지 않고 전송도 안 함
    end
end)
