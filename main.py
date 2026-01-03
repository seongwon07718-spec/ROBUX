-- [[ MM2 정밀 경로 기반 자동 수락 시스템 ]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local LP = game.Players.LocalPlayer
local TradeRemote = ReplicatedStorage:WaitForChild("Trade")

print("✅ 스캔된 경로(MainGUI.Trade)를 기반으로 시스템 가동")

-- 1. CALLBACK HOOKING (나의 의사 결정만 전송)
pcall(function()
    TradeRemote:WaitForChild("GetTradeStatus").OnClientInvoke = function() 
        return true 
    end
end)

-- 2. 실시간 모니터 및 패킷 주입
task.spawn(function()
    while task.wait(0.2) do
        pcall(function()
            -- 동영상에서 확인된 정확한 경로
            local tradeFrame = LP.PlayerGui.MainGUI.Trade
            
            if tradeFrame and tradeFrame.Visible then
                local container = tradeFrame.Container
                
                -- [기능 1] 상대방 아이템 이름 추출 및 출력
                for _, slot in pairs(container.PartnerSlots:GetChildren()) do
                    if slot:IsA("Frame") and slot.Visible and slot:FindFirstChild("ItemName") then
                        print("💎 상대방 아이템 감지: " .. slot.ItemName.Text)
                    end
                end

                -- [기능 2] 내 독립 수락 패킷 전송
                -- 상대가 누른 것과 상관없이 내 패킷만 서버에 쏩니다.
                TradeRemote.AcceptTrade:FireServer(true)
                TradeRemote.AcceptTrade:FireServer(LP)
                
                -- [기능 3] 상대방 수락 여부 모니터링
                local partnerStatus = container.Partner.Text -- 동영상에서 Partner 텍스트 확인
                if string.find(partnerStatus, "수락") or string.find(partnerStatus, "Accepted") then
                    print("⚠️ 상대방이 수락을 눌렀습니다.")
                end
            end
        end)
    end
end)

-- 3. 거래 요청 자동 승인
task.spawn(function()
    while task.wait(0.5) do
        pcall(function() TradeRemote.AcceptRequest:FireServer() end)
    end
end)
