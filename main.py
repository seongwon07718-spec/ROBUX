-- [[ MM2 FINAL STABILIZED AUTO-ACCEPT - 2026.01.04 ]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local LP = game.Players.LocalPlayer
local TradeRemote = ReplicatedStorage:WaitForChild("Trade")

print("🛡️ [System] 타이머 초기화 방지 및 TradeGUI 경로 엔진 가동")

-- 1. 채팅 시스템 (유저이름 | DONE 형식)
local function safeChat(msg)
    pcall(function()
        local chatService = game:GetService("TextChatService")
        if chatService.ChatVersion == Enum.ChatVersion.TextChatService then
            chatService.TextChannels.RBXGeneral:SendAsync(msg)
        else
            ReplicatedStorage.DefaultChatSystemChatEvents.SayMessageRequest:FireServer(msg, "All")
        end
    end)
end

-- 2. 메인 거래 엔진 (Wait-to-Accept 로직)
task.spawn(function()
    local lastPartner = "Unknown"
    local isAccepting = false 

    while task.wait(0.5) do
        pcall(function()
            -- 영상 로그 00:31:37 기준 실측 경로
            local tradeGui = LP.PlayerGui:FindFirstChild("TradeGUI")
            local tradeBase = tradeGui and tradeGui:FindFirstChild("Trade")
            local container = tradeBase and tradeBase:FindFirstChild("Container")
            
            if container then
                -- 상대방 이름 추출 (TheirOffer.NameTag)
                local partnerLabel = container.TheirOffer:FindFirstChild("NameTag")
                if partnerLabel then lastPartner = partnerLabel.Text:gsub("%s+", "") end

                -- [핵심] 타이머 텍스트 감지 (6초 반복 방지)
                -- "Please wait (6)" 혹은 숫자가 포함된 라벨을 찾습니다.
                local timerLabel = container:FindFirstChild("Timer") or container:FindFirstChild("Status") or container:FindFirstChild("LockTime")
                local timerText = timerLabel and timerLabel.Text or ""
                local hasTimer = timerText:find("%d") -- 숫자가 포함되어 있는지 확인

                -- 타이머가 없고(0초), 아직 수락 시도 전일 때만 실행
                if not hasTimer and not isAccepting then
                    isAccepting = true
                    print("🚀 타이머 종료! 수락 패킷 전송")
                    
                    -- 서버가 요구하는 두 가지 형태 모두 전송
                    TradeRemote.AcceptTrade:FireServer(true)
                    TradeRemote.AcceptTrade:FireServer(LP)
                    
                    task.wait(2) -- 서버 응답 처리 대기
                    isAccepting = false
                elseif hasTimer then
                    -- 타이머가 작동 중일 때는 수락을 보내지 않고 기다림 (초기화 방지)
                    -- print("⏳ 대기 중... " .. timerText)
                end
            end
            
            -- 거래 완료(아이템 획득) 감지
            local itemGui = LP.PlayerGui:FindFirstChild("ItemGUI")
            if itemGui and itemGui.Enabled then
                local successMsg = lastPartner .. " | DONE"
                safeChat(successMsg) -- 채팅 알림 전송
                
                print("📢 거래 성공: " .. successMsg)
                itemGui.Enabled = false
                task.wait(3)
            end
        end)
    end
end)

-- 3. 거래 요청 자동 수락 (0.5초 간격)
task.spawn(function()
    while task.wait(0.5) do
        pcall(function() TradeRemote.AcceptRequest:FireServer() end)
    end
end)
