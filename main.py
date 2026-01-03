local ReplicatedStorage = game:GetService("ReplicatedStorage")
local LP = game.Players.LocalPlayer
local TradeRemote = ReplicatedStorage:WaitForChild("Trade")

print("🛡️ [System] 지능형 감시 모드 가동 - 타이머 종료 및 상대 수락 대기 중")

-- 1. 채팅 알림 함수
local function sendChat(msg)
    pcall(function()
        game:GetService("TextChatService").TextChannels.RBXGeneral:SendAsync(msg)
    end)
end

-- 2. 핵심 로직: 서버 신호 도청 (RemoteEvent Listening)
local partnerAccepted = false
local canFinalAccept = false

-- 서버가 보내는 거래 업데이트 신호를 감시하여 상태 파악
TradeRemote.UpdateTrade.OnClientEvent:Connect(function(data)
    pcall(function()
        -- 상대방이 수락 버튼을 눌렀는지 확인
        if data.Accepted == true then
            partnerAccepted = true
            print("👤 상대방이 수락을 눌렀습니다.")
        else
            partnerAccepted = false
        end
        
        -- 타이머(LockTime)가 0이 되었는지 확인
        if data.CanAccept == true or (data.LockTime and data.LockTime <= 0) then
            canFinalAccept = true
            print("✅ 타이머 종료 - 수락 가능 상태")
        elseif not data.LockTime then
            -- LockTime이 없는 경우 타이머 종료로 간주
            canFinalAccept = true
            print("✅ LockTime 없음 - 수락 가능 상태")
        end
    end)
end)

-- 3. 실행 엔진: 조건이 충족될 때만 '단 한 번' 발사
task.spawn(function()
    while task.wait(0.5) do
        pcall(function()
            -- 조건: 1. 숫자가 사라짐(0초) AND 2. 상대방이 수락함
            if canFinalAccept and partnerAccepted then
                print("🚀 모든 조건 충족! 최종 수락 신호 전송")
                
                -- 수락을 전송
                TradeRemote.AcceptTrade:FireServer(true)
                
                -- 수락 후 잠시 대기하여 중복 전송 방지 (6초 리셋 방지)
                task.wait(2)
            else
                print("❌ 수락 조건 미충족 (canFinalAccept: " .. tostring(canFinalAccept) .. ", partnerAccepted: " .. tostring(partnerAccepted) .. ")")
            end
            
            -- 거래 완료(성공) 감지
            local itemGui = LP.PlayerGui:FindFirstChild("ItemGUI")
            if itemGui and itemGui.Enabled then
                sendChat("SUCCESS | DONE")
                itemGui.Enabled = false
                canFinalAccept = false
                partnerAccepted = false
                task.wait(3)
            end
        end)
    end
end)

-- 4. 거래 요청 자동 승인
local lastRequestTime = 0
task.spawn(function()
    while task.wait(1) do
        -- 1초 간격으로 반복 호출하는 대신 조건을 넣어서 불필요한 호출 방지
        if tick() - lastRequestTime > 5 then  -- 5초 이상 간격이 있을 때만 요청
            pcall(function() 
                TradeRemote.AcceptRequest:FireServer() 
            end)
            lastRequestTime = tick()
        end
    end
end)
