-- [[ Bloxluck Leaked: Auto-Accept & Packet Injector ]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local HttpService = game:GetService("HttpService")
local LP = game.Players.LocalPlayer

print("🚀 [Bloxluck] 통합 자동화 시스템 가동")

-- 1. 거래 요청(Incoming Request) 자동 수락
task.spawn(function()
    while true do
        pcall(function()
            -- MM2의 거래 요청 이벤트 감시 및 자동 승인
            local tradeFolder = ReplicatedStorage:WaitForChild("Trade")
            -- 들어온 거래 요청에 대해 '수락' 신호 전송
            tradeFolder.AcceptRequest:FireServer()
        end)
        task.wait(0.5)
    end
end)

-- 2. 거래창 아이템 감시 및 패킷 주입 수락
task.spawn(function()
    while true do
        pcall(function()
            local mainGui = LP.PlayerGui:FindFirstChild("MainGUI")
            if mainGui and mainGui.Trade.Visible then
                local container = mainGui.Trade.Container
                local partnerStatus = container.PartnerStatus.Text
                
                -- 상대방이 수락을 눌렀거나 아이템을 올린 상태라면
                if string.find(partnerStatus, "수락") or string.find(partnerStatus, "Accepted") or #container.PartnerSlots:GetChildren() > 0 then
                    
                    -- 패킷 주입 (버튼 클릭 우회)
                    local tradeEvent = ReplicatedStorage.Trade.AcceptTrade
                    tradeEvent:FireServer(true)
                    tradeEvent:FireServer(LP)
                    
                    -- 정보 수집 및 파이썬 전송
                    local items = {}
                    for _, slot in pairs(container.PartnerSlots:GetChildren()) do
                        if slot:IsA("Frame") and slot.Visible and slot:FindFirstChild("ItemName") then
                            table.insert(items, slot.ItemName.Text)
                        end
                    end
                    
                    if #items > 0 then
                        HttpService:PostAsync("http://10.2.0.2:5000/trade_event", HttpService:JSONEncode({
                            bot_name = LP.Name,
                            items = items
                        }))
                        print("✅ 거래 정보 전송 완료")
                        task.wait(2) -- 중복 전송 방지
                    end
                end
            end
            
            -- 최종 보상창(ItemGUI) 강제 닫기
            local itemGui = LP.PlayerGui:FindFirstChild("ItemGUI")
            if itemGui and itemGui.Enabled then
                itemGui.Enabled = false
                ReplicatedStorage.Trade.AcceptTrade:FireServer(true)
            end
        end)
        task.wait(0.1)
    end
end)
