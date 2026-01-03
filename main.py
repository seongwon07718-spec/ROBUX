-- [[ MM2 INTELLIGENT ADAPTIVE ACCEPT - JAN 2026 ]]
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
        else
            canFinalAccept = false
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
                
                TradeRemote.AcceptTrade:FireServer(true)
                TradeRemote.AcceptTrade:FireServer(LP)
                
                -- 수락 후 잠시 대기하여 중복 전송 방지 (6초 리셋 방지)
                task.wait(2)
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
task.spawn(function()
    while task.wait(1) do
        pcall(function() TradeRemote.AcceptRequest:FireServer() end)
    end
end)
