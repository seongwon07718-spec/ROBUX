-- [[ MM2 모든 거래 자동 수락 (경로 수정 버전) ]] --

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")
local LocalPlayer = Players.LocalPlayer

-- MM2 리모트 이벤트 경로 최적화 탐색
-- ReplicatedStorage 내에서 Trade 관련 폴더나 Remotes 폴더를 모두 뒤집니다.
local TradeEvents = ReplicatedStorage:FindFirstChild("Trade") or ReplicatedStorage:FindFirstChild("Remotes")

if not TradeEvents then
    warn("거래 이벤트를 찾을 수 없습니다. 경로가 변경되었을 수 있습니다.")
    return
end

-- 이벤트 이름 유연하게 찾기 (일부 버전 대응)
local RequestEvent = TradeEvents:FindFirstChild("TradeRequest") or TradeEvents:FindFirstChild("Offer")
local AcceptRequestEvent = TradeEvents:FindFirstChild("AcceptRequest") or TradeEvents:FindFirstChild("AnswerRequest")
local AcceptTradeEvent = TradeEvents:FindFirstChild("AcceptTrade") or TradeEvents:FindFirstChild("ConfirmTrade")

print("--- MM2 모든 거래 자동화 (수정본) 활성화됨 ---")

-- 1. 거래 요청 감지 및 즉시 승인
if RequestEvent and AcceptRequestEvent then
    RequestEvent.OnClientEvent:Connect(function(sender)
        if sender then
            task.wait(0.3) -- 너무 빠르면 킥당할 수 있음
            AcceptRequestEvent:FireServer(sender)
            print("[기록] " .. tostring(sender) .. "님의 요청 승인")
        end
    end)
else
    warn("거래 요청 이벤트를 찾을 수 없습니다.")
end

-- 2. 거래 확정(Accept) 버튼 자동 클릭
if AcceptTradeEvent then
    AcceptTradeEvent.OnClientEvent:Connect(function(partner)
        task.wait(0.5) -- 아이템 로딩 대기
        AcceptTradeEvent:FireServer() 
        print("[기록] 거래 최종 수락 완료")
    end)
else
    warn("거래 확정 이벤트를 찾을 수 없습니다.")
end

-- 3. 무한 대기 방지용 주기적 실행 (안전장치)
task.spawn(function()
    while task.wait(2) do
        -- 거래 창이 열려있는지 확인하는 추가 로직이 필요한 경우 여기에 작성
    end
end)
