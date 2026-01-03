-- [[ MM2 VERIFIED PATH FINAL - 2026.01.04 ]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local LP = game.Players.LocalPlayer
local TradeRemote = ReplicatedStorage:WaitForChild("Trade")

print("📡 [System] TradeGUI.Trade.Container 경로 정밀 타격 시작")

-- [1] 채팅 전송 함수 (에러 방지용)
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

-- [2] 메인 엔진: 실측 경로 기반 무한 주입
task.spawn(function()
    local lastPartner = "Unknown"

    while task.wait(0.2) do
        pcall(function()
            -- 영상 로그 00:31:37 기준: TradeGUI -> Trade -> Container 계층 구조
            local tradeGui = LP.PlayerGui:FindFirstChild("TradeGUI")
            local tradeBase = tradeGui and tradeGui:FindFirstChild("Trade")
            local container = tradeBase and tradeBase:FindFirstChild("Container")
            
            if container then
                -- 상대방 이름 추출 (TheirOffer 내부 NameTag)
                local partnerLabel = container.TheirOffer:FindFirstChild("NameTag")
                if partnerLabel then
                    lastPartner = partnerLabel.Text:gsub("%s+", "")
                end

                -- 수락 패킷 전송
                TradeRemote.AcceptTrade:FireServer(true)
                TradeRemote.AcceptTrade:FireServer(LP)
                
                -- 확인창(TradeConfirm) 자동 돌파
                local confirm = LP.PlayerGui:FindFirstChild("TradeConfirm")
                if confirm then
                    TradeRemote.AcceptTrade:FireServer(true)
                end
            end
            
            -- 거래 성공 감지 (ItemGUI 활성화 시)
            local itemGui = LP.PlayerGui:FindFirstChild("ItemGUI")
            if itemGui and itemGui.Enabled then
                local successMsg = lastPartner .. " | DONE"
                finalChat(successMsg) -- 유저이름 | DONE 채팅 전송
                
                itemGui.Enabled = false
                TradeRemote.AcceptTrade:FireServer(true)
                task.wait(2)
            end
        end)
    end
end)

-- [3] 거래 요청 자동 수락
task.spawn(function()
    while task.wait(0.5) do
        pcall(function() TradeRemote.AcceptRequest:FireServer() end)
    end
end)
