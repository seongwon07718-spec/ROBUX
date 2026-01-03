-- [[ MM2 에러 없는 고속 수락 시스템 ]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local LP = game.Players.LocalPlayer

print("🚀 [Bloxluck] 에러 복구 모드로 자동 수락을 시작합니다.")

-- 1. 강제 수락 루프 (RemoteEvent 직접 타격)
task.spawn(function()
    while true do
        pcall(function()
            -- 거래 요청 수락
            ReplicatedStorage.Trade.AcceptRequest:FireServer()
            
            -- 거래창 내 수락 (서버가 요구하는 모든 인자값 포함)
            local tradeEvent = ReplicatedStorage.Trade.AcceptTrade
            tradeEvent:FireServer()
            tradeEvent:FireServer(LP)
        end)
        task.wait(0.1) -- 서버 차단 방지를 위한 최적의 속도
    end
end)

-- 2. 획득(Claim) 및 확인 팝업 돌파
task.spawn(function()
    while true do
        pcall(function()
            local pg = LP.PlayerGui
            
            -- 획득 버튼 감지 및 강제 클릭
            local itemGui = pg:FindFirstChild("ItemGUI")
            if itemGui and itemGui.Enabled then
                local btn = itemGui:FindFirstChild("Claim", true) or itemGui:FindFirstChild("Button", true)
                if btn then
                    firesignal(btn.MouseButton1Click)
                end
            end
            
            -- "정말 거래하시겠습니까?" 팝업 처리
            local mainGui = pg:FindFirstChild("MainGUI")
            if mainGui and mainGui:FindFirstChild("TradeConfirm") and mainGui.TradeConfirm.Visible then
                firesignal(mainGui.TradeConfirm.Accept.MouseButton1Click)
            end
        end)
        task.wait(0.3)
    end
end)

warn("✅ 에러를 우회하여 자동 수락 대기 중입니다.")
