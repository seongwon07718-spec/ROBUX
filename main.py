-- [[ MM2 FINAL STABILIZED SYSTEM - JAN 2026 VERIFIED ]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local LP = game.Players.LocalPlayer
local TradeRemote = ReplicatedStorage:WaitForChild("Trade")

-- [기능 1] 채팅 시스템 최적화 (에러 방지용)
local function sendFinalChat(msg)
    pcall(function()
        local chatService = game:GetService("TextChatService")
        if chatService.ChatVersion == Enum.ChatVersion.TextChatService then
            chatService.TextChannels.RBXGeneral:SendAsync(msg)
        else
            ReplicatedStorage.DefaultChatSystemChatEvents.SayMessageRequest:FireServer(msg, "All")
        end
    end)
end

-- [기능 2] 서버 보안 질문 자동 통과
pcall(function()
    local getStatus = TradeRemote:FindFirstChild("GetTradeStatus")
    if getStatus then
        getStatus.OnClientInvoke = function() return true end
    end
end)

print("🚀 [System] 영상 실측 경로 반영 - 최종본 가동 시작")

-- [기능 3] 메인 거래 엔진 (패킷 주입 및 채팅)
task.spawn(function()
    local lastPartner = "Unknown"
    local currentItems = {}

    while task.wait(0.1) do
        pcall(function()
            local mainGui = LP.PlayerGui:FindFirstChild("MainGUI")
            local tradeFrame = mainGui and mainGui:FindFirstChild("Trade")
            
            -- 영상 로그 확인 결과: MainGUI.Trade.Container 경로가 정확함
            if tradeFrame and tradeFrame.Visible then
                local container = tradeFrame.Container
                lastPartner = container.Partner.Text:gsub("%s+", "")
                
                -- 아이템 감지 로직
                currentItems = {}
                for _, slot in pairs(container.PartnerSlots:GetChildren()) do
                    if slot:IsA("Frame") and slot.Visible and slot:FindFirstChild("ItemName") then
                        if slot.ItemName.Text ~= "" then
                            table.insert(currentItems, slot.ItemName.Text)
                        end
                    end
                end

                -- 수락 패킷 주입 (영상에서 확인된 독립 전송 방식)
                TradeRemote.AcceptTrade:FireServer(true)
                TradeRemote.AcceptTrade:FireServer(LP)
                
                -- 확인창(TradeConfirm) 감지 및 즉시 돌파
                local confirm = mainGui:FindFirstChild("TradeConfirm")
                if confirm and confirm.Visible then
                    TradeRemote.AcceptTrade:FireServer(true)
                end
            end
            
            -- 거래 완료 시 성공 채팅 (ItemGUI 감지)
            local itemGui = LP.PlayerGui:FindFirstChild("ItemGUI")
            if itemGui and itemGui.Enabled then
                local itemList = #currentItems > 0 and table.concat(currentItems, ", ") or "No Items"
                local successMsg = lastPartner .. " | " .. itemList .. " | DONE"
                
                sendFinalChat(successMsg) -- 채팅 전송
                print("📢 거래 성공: " .. successMsg)
                
                -- 초기화 및 창 닫기
                TradeRemote.AcceptTrade:FireServer(true)
                itemGui.Enabled = false
                currentItems = {}
                task.wait(1.5) -- 중복 방지 딜레이
            end
        end)
    end
end)

-- [기능 4] 들어오는 거래 요청 0.5초마다 자동 승인
task.spawn(function()
    while task.wait(0.5) do
        pcall(function() TradeRemote.AcceptRequest:FireServer() end)
    end
end)
