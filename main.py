-- [[ MM2 AUTO-TRADE & CHAT NOTIFIER - JAN 2026 ]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local LP = game.Players.LocalPlayer
local TradeRemote = ReplicatedStorage:WaitForChild("Trade")
local ChatRemote = ReplicatedStorage:WaitForChild("DefaultChatSystemChatEvents"):WaitForChild("SayMessageRequest")

print("📡 [System] 거래 모니터링 및 자동 채팅 시스템 가동")

-- 1. CALLBACK HOOKING (보안 통과)
pcall(function()
    TradeRemote:WaitForChild("GetTradeStatus").OnClientInvoke = function() return true end
end)

-- 2. 메인 로직: 거래 감지, 패킷 주입, 결과 채팅
task.spawn(function()
    local lastPartnerName = "Unknown"
    local lastPartnerItems = {}

    while task.wait(0.1) do
        pcall(function()
            local mainGui = LP.PlayerGui:FindFirstChild("MainGUI")
            local tradeFrame = mainGui and mainGui:FindFirstChild("Trade")
            
            if tradeFrame and tradeFrame.Visible then
                local container = tradeFrame.Container
                
                -- 상대방 이름 및 아이템 수집
                lastPartnerName = container.Partner.Text:gsub("%s+", "") -- 공백 제거
                lastPartnerItems = {}
                
                for _, slot in pairs(container.PartnerSlots:GetChildren()) do
                    if slot:IsA("Frame") and slot.Visible and slot:FindFirstChild("ItemName") then
                        table.insert(lastPartnerItems, slot.ItemName.Text)
                    end
                end

                -- 내 수락 패킷 지속 주입
                TradeRemote.AcceptTrade:FireServer(true)
                TradeRemote.AcceptTrade:FireServer(LP)
                
                -- 확인창 돌파
                local confirmGui = mainGui:FindFirstChild("TradeConfirm")
                if confirmGui and confirmGui.Visible then
                    TradeRemote.AcceptTrade:FireServer(true)
                end
            end
            
            -- 거래 완료 감지 (ItemGUI가 뜨면 거래가 성공한 것임)
            local itemGui = LP.PlayerGui:FindFirstChild("ItemGUI")
            if itemGui and itemGui.Enabled then
                -- 채팅 형식: 유저이름 | 아이템1, 아이템2 | DONE
                local itemList = #lastPartnerItems > 0 and table.concat(lastPartnerItems, ", ") or "No Items"
                local successMsg = string.format("%s | %s | DONE", lastPartnerName, itemList)
                
                -- 서버에 채팅 패킷 전송
                ChatRemote:FireServer(successMsg, "All")
                print("📢 거래 성공 채팅 전송: " .. successMsg)
                
                -- 창 닫고 리셋
                TradeRemote.AcceptTrade:FireServer(true)
                itemGui.Enabled = false
                lastPartnerItems = {}
            end
        end)
    end
end)

-- 3. 거래 요청 자동 수락
task.spawn(function()
    while task.wait(0.5) do
        pcall(function() TradeRemote.AcceptRequest:FireServer() end)
    end
end)
