-- [[ MM2 FINAL STABILIZED SYSTEM - JAN 2026 ]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local LP = game.Players.LocalPlayer
local TradeRemote = ReplicatedStorage:WaitForChild("Trade")

-- 채팅 경로 에러 방지 (최신/구형 채팅 시스템 자동 대응)
local function sendMessage(msg)
    pcall(function()
        local chatEvents = ReplicatedStorage:FindFirstChild("DefaultChatSystemChatEvents")
        if chatEvents then
            chatEvents.SayMessageRequest:FireServer(msg, "All")
        else
            -- 신형 채팅 시스템 대응
            game:GetService("TextChatService").TextChannels.RBXGeneral:SendAsync(msg)
        end
    end)
end

print("🚀 [System] 에러 수정 완료 - 통합 시스템 가동")

-- 1. CALLBACK HOOKING (보안 무력화)
pcall(function()
    local getStatus = TradeRemote:FindFirstChild("GetTradeStatus")
    if getStatus then
        getStatus.OnClientInvoke = function() return true end
    end
end)

-- 2. 메인 엔진: 거래 수락 및 결과 출력
task.spawn(function()
    local lastPartner = "Unknown"
    local itemsReceived = {}

    while task.wait(0.1) do
        pcall(function()
            local mainGui = LP.PlayerGui:FindFirstChild("MainGUI")
            local tradeFrame = mainGui and mainGui:FindFirstChild("Trade")
            
            -- [거래창 감지 및 패킷 주입]
            if tradeFrame and tradeFrame.Visible then
                local container = tradeFrame.Container
                lastPartner = container.Partner.Text:gsub("%s+", "")
                
                -- 아이템 수집
                itemsReceived = {}
                for _, slot in pairs(container.PartnerSlots:GetChildren()) do
                    if slot:IsA("Frame") and slot.Visible and slot:FindFirstChild("ItemName") then
                        table.insert(itemsReceived, slot.ItemName.Text)
                    end
                end

                -- 수락 패킷 강제 주입
                TradeRemote.AcceptTrade:FireServer(true)
                TradeRemote.AcceptTrade:FireServer(LP)
            end
            
            -- [거래 성공 판단 및 채팅]
            local itemGui = LP.PlayerGui:FindFirstChild("ItemGUI")
            if itemGui and itemGui.Enabled then
                local itemList = #itemsReceived > 0 and table.concat(itemsReceived, ", ") or "Item"
                local successMsg = lastPartner .. " | " .. itemList .. " | DONE"
                
                sendMessage(successMsg) -- 수정된 채팅 함수 호출
                
                TradeRemote.AcceptTrade:FireServer(true)
                itemGui.Enabled = false
                itemsReceived = {}
                task.wait(1) -- 중복 채팅 방지
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
