-- [[ MM2 모든 유저 자동 거래 수락 스크립트 ]] --

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")
local LocalPlayer = Players.LocalPlayer

-- MM2 거래 관련 리모트 이벤트 경로 설정
local TradeEvents = ReplicatedStorage:WaitForChild("Trade")
local AcceptRequest = TradeEvents:WaitForChild("AcceptRequest") -- 거래 요청 승인
local AcceptTrade = TradeEvents:WaitForChild("AcceptTrade")     -- 거래 확정 수락

print("--- MM2 모든 거래 자동화 활성화됨 ---")

-- 1. 거래 요청이 오면 무조건 승인 (누가 걸든 상관없음)
TradeEvents:WaitForChild("TradeRequest").OnClientEvent:Connect(function(sender)
    if sender then
        AcceptRequest:FireServer(sender)
        print("[기록] " .. sender.Name .. "님의 거래 요청을 승인했습니다.")
    end
end)

-- 2. 거래 창에서 아이템이 올라오면(또는 대기 중이면) 즉시 수락 버튼 클릭
-- partner가 누구든 조건 없이 FireServer를 보냅니다.
TradeEvents:WaitForChild("AcceptTrade").OnClientEvent:Connect(function(partner)
    -- 약간의 딜레이를 주어 서버 튕김 방지 (0.5초)
    task.wait(0.5)
    AcceptTrade:FireServer() 
    
    local partnerName = (type(partner) == "table" and partner.Name) or tostring(partner)
    print("[기록] " .. partnerName .. "님과의 거래를 최종 수락했습니다.")
end)

-- 3. 추가: 거래 창이 열렸을 때 자동으로 수락 상태를 유지하는 루프 (안전장치)
-- 일부 실행기에서 이벤트가 누락되는 경우를 방지합니다.
task.spawn(function()
    while task.wait(1) do
        -- 현재 거래 중인지 체크하는 로직 (MM2 내부 변수 참조)
        -- 필요한 경우 여기에 추가적인 수락 강제 코드를 넣을 수 있습니다.
    end
end)

print("모든 사람 거래 가능 모드 작동 중...")
