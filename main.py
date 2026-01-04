local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Player = game.Players.LocalPlayer
local TradeAPI = ReplicatedStorage:WaitForChild("Remotes"):WaitForChild("TradeAPI") -- 경로 확인 필요

-- 거래창 데이터에서 현재 TradeID를 가져오는 함수 (가장 핵심)
local function getTradeId()
    local tradeGui = Player.PlayerGui:FindFirstChild("TradeGUI") -- 이름은 다를 수 있음
    if tradeGui and tradeGui:FindFirstChild("TradeID") then
        return tradeGui.TradeID.Value
    end
    return nil
end

-- 자동 수락 메인 루프
task.spawn(function()
    while task.wait(0.5) do
        local currentId = getTradeId()
        
        pcall(function()
            -- 1. 일단 요청이 오면 무조건 수락
            TradeAPI:FireServer("AcceptRequest")
            
            -- 2. 거래창이 열려 있고 ID가 있다면 1, 2차 수락 진행
            if currentId then
                TradeAPI:FireServer("AcceptTrade", currentId)
                task.wait(1.5) -- 서버 검증 대기 시간
                TradeAPI:FireServer("ConfirmTrade", currentId)
                print("거래 ID [" .. tostring(currentId) .. "] 최종 수락 시도")
            end
        end)
    end
end)
