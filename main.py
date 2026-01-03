-- [[ MM2 FINAL STABILIZED SYSTEM - VERIFIED PATH ]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local LP = game.Players.LocalPlayer
local TradeRemote = ReplicatedStorage:WaitForChild("Trade")

print("🚀 [System] 영상 실측 경로(TradeGUI) 기반 최종본 가동")

-- 1. 채팅 시스템 (솔라라 최적화 버전)
local function finalChat(msg)
    pcall(function()
        local chatService = game:GetService("TextChatService")
        if chatService.ChatVersion == Enum.ChatVersion.TextChatService then
            chatService.TextChannels.RBXGeneral:SendAsync(msg)
        else
            ReplicatedStorage.DefaultChatSystemChatEvents.SayMessageRequest:FireServer(msg, "All")
        end
    end)
end

-- 2. 메인 거래 엔진 (패킷 주입 및 자동 수락)
task.spawn(function()
    local lastPartner = "Unknown"

    while task.wait(0.3) do
        pcall(function()
            -- 영상 로그 00:31:37 확인: MainGUI가 아닌 TradeGUI 사용
            local tradeGui = LP.PlayerGui:FindFirstChild("TradeGUI")
            
            -- TradeGUI가 존재하면 활성화된 것으로 간주 (Visible 에러 회피)
            if tradeGui then
                -- 상대방 이름 추출 (영상 실측 경로)
                local container = tradeGui:FindFirstChild("Container")
                if container and container:FindFirstChild("Trade") then
                    local partnerLabel = container.Trade.TheirOffer:FindFirstChild("NameTag")
                    if partnerLabel then
                        lastPartner = partnerLabel.Text:gsub("%s+", "")
                    end
                end

                -- 수락 패킷 강제 주입 (Brute-force)
                TradeRemote.AcceptTrade:FireServer(true)
                TradeRemote.AcceptTrade:FireServer(LP)
                
                -- 확인창(TradeConfirm) 자동 돌파
                local confirm = LP.PlayerGui:FindFirstChild("TradeConfirm")
                if confirm then
                    TradeRemote.AcceptTrade:FireServer(true)
                end
            end
            
            -- 거래 완료 감지 및 채팅 알림
            local itemGui = LP.PlayerGui:FindFirstChild("ItemGUI")
            if itemGui and itemGui.Enabled then
                local successMsg = string.format("%s | DONE", lastPartner)
                finalChat(successMsg)
                
                print("📢 거래 성공: " .. successMsg)
                itemGui.Enabled = false
                TradeRemote.AcceptTrade:FireServer(true)
                task.wait(2) -- 중복 처리 방지
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
