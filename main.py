-- [[ MM2 MOBILE (LD PLAYER) ULTIMATE ADAPTIVE ]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local LP = game.Players.LocalPlayer
local TradeRemote = ReplicatedStorage:WaitForChild("Trade")

print("📱 [Mobile System] 모바일 전용 엔진 가동 - LD플레이어 최적화")

-- 1. 채팅 함수
local function sendChat(msg)
    pcall(function()
        game:GetService("TextChatService").TextChannels.RBXGeneral:SendAsync(msg)
    end)
end

-- 2. 핵심 변수
local partnerAccepted = false

-- 서버 신호 감시
TradeRemote.UpdateTrade.OnClientEvent:Connect(function(data)
    pcall(function()
        if data.Accepted and tostring(data.Accepted) ~= LP.Name then
            partnerAccepted = true
        elseif data.Accepted == nil or data.Accepted == false then
            partnerAccepted = false
        end
    end)
end)

-- 3. 모바일 UI 정밀 감시 및 실행 엔진
task.spawn(function()
    while task.wait(0.3) do
        pcall(function()
            -- 모바일 MM2 전용 GUI 경로 [MainGUI -> Trade]
            local mainGui = LP.PlayerGui:FindFirstChild("MainGUI")
            local tradeFrame = mainGui and mainGui:FindFirstChild("Trade")
            
            if tradeFrame and tradeFrame.Visible then
                -- 모바일 수락 버튼 위치 (Accept 또는 Confirm)
                local acceptBtn = tradeFrame:FindFirstChild("Accept") or tradeFrame:FindFirstChild("Confirm")
                
                -- 타이머 숫자 확인 (Status 라벨)
                local statusLabel = tradeFrame:FindFirstChild("Status")
                local timerText = statusLabel and statusLabel.Text or ""
                local isTimerDone = not timerText:find("%d") -- 숫자가 없으면 0초
                
                -- 상대방 상태 확인 (Status_Partner 또는 유사 경로)
                local partnerStatus = tradeFrame:FindFirstChild("PartnerStatus") or tradeFrame:FindFirstChild("Status2")
                local uiPartnerAccepted = partnerStatus and (partnerStatus.Text:find("Accepted") or partnerStatus.Text:find("수락"))

                -- 수락 조건 충족 시
                if isTimerDone and (partnerAccepted or uiPartnerAccepted) then
                    if acceptBtn then
                        -- 모바일 실행기(Fluxus/Hydrogen) 함수 호출
                        if getconnections then
                            for _, v in pairs(getconnections(acceptBtn.MouseButton1Click)) do v:Fire() end
                        end
                        
                        -- 패킷 전송
                        TradeRemote.AcceptTrade:FireServer(true)
                        print("✅ [Mobile] 수락 성공")
                        task.wait(2)
                    end
                end
            end
            
            -- 거래 성공 감지 (ItemGUI)
            local itemGui = LP.PlayerGui:FindFirstChild("ItemGUI")
            if itemGui and itemGui.Enabled then
                sendChat("MOBILE SUCCESS | DONE")
                itemGui.Enabled = false
                task.wait(3)
            end
        end)
    end
end)

-- 거래 요청 자동 승인
task.spawn(function()
    while task.wait(2) do
        pcall(function() TradeRemote.AcceptRequest:FireServer() end)
    end
end)
