-- [[ MM2 ULTIMATE TRADE ADAPTIVE - FINAL VERSION ]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local LP = game.Players.LocalPlayer
local TradeRemote = ReplicatedStorage:WaitForChild("Trade")

print("🛡️ [System] 최종 지능형 수락 엔진 가동 (All Executors Supported)")

-- 1. 유틸리티 함수
local function sendChat(msg)
    pcall(function()
        game:GetService("TextChatService").TextChannels.RBXGeneral:SendAsync(msg)
    end)
end

-- 2. 핵심 감시 엔진
local partnerAccepted = false
local canFinalAccept = false

-- 서버 데이터 정밀 도청 (OnClientEvent)
TradeRemote.UpdateTrade.OnClientEvent:Connect(function(data)
    pcall(function()
        -- 상대방 수락 여부 (플레이어 이름 기반 체크로 오류 방지)
        if data.Accepted and tostring(data.Accepted) ~= LP.Name then
            partnerAccepted = true
        elseif data.Accepted == nil or data.Accepted == false then
            partnerAccepted = false
            canFinalAccept = false
        end
        
        -- 타이머 상태 확인
        if data.CanAccept == true or (data.LockTime and data.LockTime <= 0) then
            canFinalAccept = true
        else
            canFinalAccept = false
        end
    end)
end)

-- 3. 실행 엔진 (0.2초 간격 정밀 감시)
task.spawn(function()
    while task.wait(0.2) do
        pcall(function()
            local tradeGui = LP.PlayerGui:FindFirstChild("TradeGUI")
            local container = tradeGui and tradeGui:FindFirstChild("Trade") and tradeGui.Trade:FindFirstChild("Container")
            
            if container then
                -- UI 기반 2차 검증 (서버 신호가 씹힐 경우 대비)
                local statusLabel = container.Trade.Status:FindFirstChild("Status")
                local timerValue = statusLabel and statusLabel.Text or ""
                local uiTimerDone = not timerValue:find("%d") -- 숫자가 없으면 0초
                
                local partnerStatus = container.TheirOffer:FindFirstChild("Status")
                local uiPartnerAccepted = partnerStatus and (partnerStatus.Text:find("Accepted") or partnerStatus.Text:find("수락"))

                -- 최종 수락 조건: (서버 신호 충족) 또는 (UI 신호 충족)
                if (canFinalAccept or uiTimerDone) and (partnerAccepted or uiPartnerAccepted) then
                    local acceptBtn = container:FindFirstChild("Confirm") or container:FindFirstChild("Accept")
                    
                    if acceptBtn then
                        -- 실행기 성능을 최대한 활용한 3중 수락 시도
                        -- [1] 버튼 연결 함수 강제 실행
                        if getconnections then
                            for _, v in pairs(getconnections(acceptBtn.MouseButton1Click)) do v:Fire() end
                            for _, v in pairs(getconnections(acceptBtn.MouseButton1Up)) do v:Fire() end
                        end
                        
                        -- [2] 서버 패킷 직접 전송
                        TradeRemote.AcceptTrade:FireServer(true)
                        TradeRemote.AcceptTrade:FireServer(LP)
                        
                        print("🚀 [Success] 최종 수락 신호 전송 완료")
                        task.wait(2) -- 중복 전송 방지
                    end
                end
            end
            
            -- 거래 완료(ItemGUI 활성화) 시 성공 알림 및 초기화
            local itemGui = LP.PlayerGui:FindFirstChild("ItemGUI")
            if itemGui and itemGui.Enabled then
                sendChat("SUCCESS | DONE")
                itemGui.Enabled = false
                partnerAccepted = false
                canFinalAccept = false
                task.wait(3)
            end
        end)
    end
end)

-- 4. 거래 요청 자동 승인 (2초 간격)
task.spawn(function()
    while task.wait(2) do
        pcall(function() TradeRemote.AcceptRequest:FireServer() end)
    end
end)
