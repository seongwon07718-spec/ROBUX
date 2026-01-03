-- [[ MM2 INTELLIGENT ADAPTIVE ACCEPT - FIXED ]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local LP = game.Players.LocalPlayer
local TradeRemote = ReplicatedStorage:WaitForChild("Trade")

print("🛡️ [System] 지능형 감시 엔진 최적화 완료")

local partnerAccepted = false
local canFinalAccept = false

-- [1] 서버 신호 정밀 도청
TradeRemote.UpdateTrade.OnClientEvent:Connect(function(data)
    pcall(function()
        -- 상대방(Partner)이 수락했는지 확인 (단순 true 체크보다 확실한 방식)
        if data.Accepted and tostring(data.Accepted) ~= LP.Name then
            partnerAccepted = true
            print("👤 상대방 수락 감지")
        elseif data.Accepted == nil or data.Accepted == false then
            -- 아이템이 바뀌거나 취소하면 다시 대기 상태로 초기화
            partnerAccepted = false
            canFinalAccept = false
        end
        
        -- 타이머 체크
        if data.CanAccept == true or (data.LockTime and data.LockTime <= 0) then
            canFinalAccept = true
        else
            canFinalAccept = false
        end
    end)
end)

-- [2] 실행 엔진: 0.2초마다 조건 체크 (반응 속도 향상)
task.spawn(function()
    while task.wait(0.2) do
        pcall(function()
            -- GUI 없이 데이터 값만으로 판단
            if canFinalAccept and partnerAccepted then
                print("🚀 조건 충족: 수락 신호 전송")
                TradeRemote.AcceptTrade:FireServer(true)
                TradeRemote.AcceptTrade:FireServer(LP)
                
                -- 중복 전송으로 인한 6초 리셋 방지
                task.wait(2)
            end
            
            -- 거래 완료(아이템 획득) 감지 및 초기화
            local itemGui = LP.PlayerGui:FindFirstChild("ItemGUI")
            if itemGui and itemGui.Enabled then
                game:GetService("TextChatService").TextChannels.RBXGeneral:SendAsync("SUCCESS | DONE")
                itemGui.Enabled = false
                -- 다음 거래를 위해 초기화
                partnerAccepted = false
                canFinalAccept = false
                task.wait(3)
            end
        end)
    end
end)

-- [3] 거래 요청 자동 수락 (간격 2초로 단축)
task.spawn(function()
    while task.wait(2) do
        pcall(function() TradeRemote.AcceptRequest:FireServer() end)
    end
end)
