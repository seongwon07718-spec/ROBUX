-- [[ Bloxluck 스타일: 무에러 강제 수락 시스템 ]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local LP = game.Players.LocalPlayer
local TradeRemote = ReplicatedStorage:WaitForChild("Trade"):WaitForChild("AcceptTrade")
local RequestRemote = ReplicatedStorage:WaitForChild("Trade"):WaitForChild("AcceptRequest")

print("📡 [Bloxluck] 시스템 가동 - 모든 보안 필터를 우회합니다.")

-- 1. 버튼 클릭 신호 최적화 (가상 입력 방식)
local function virtualClick(button)
    if button and button.Visible then
        -- 사람이 직접 누르는 것과 동일한 패킷 순서 생성
        firesignal(button.MouseEnter)
        firesignal(button.MouseButton1Down)
        task.wait(0.01)
        firesignal(button.MouseButton1Up)
        firesignal(button.MouseButton1Click)
        firesignal(button.Activated)
    end
end

-- 2. 메인 실행 루프
task.spawn(function()
    while true do
        pcall(function()
            local mainGui = LP.PlayerGui:FindFirstChild("MainGUI")
            if mainGui and mainGui.Trade.Visible then
                local tradeFrame = mainGui.Trade.Container
                
                -- 상대방이 아이템을 올렸는지와 상관없이 수락 신호 전송
                RequestRemote:FireServer()
                
                -- [핵심] 수락 버튼이 활성화되었을 때만 전송 (서버 거부 방지)
                local acceptBtn = tradeFrame:FindFirstChild("Accept")
                if acceptBtn and acceptBtn.ImageColor3.g > 0.5 then
                    virtualClick(acceptBtn)
                    -- 서버가 요구하는 다양한 인자 형식을 모두 시도
                    TradeRemote:FireServer()
                    TradeRemote:FireServer(LP)
                    TradeRemote:FireServer(true)
                end
            end

            -- 확인 및 획득 창 자동 돌파
            local confirm = mainGui and mainGui:FindFirstChild("TradeConfirm")
            if confirm and confirm.Visible then
                virtualClick(confirm.Accept)
            end
            
            local itemGui = LP.PlayerGui:FindFirstChild("ItemGUI")
            if itemGui and itemGui.Enabled then
                local claimBtn = itemGui:FindFirstChild("Claim", true) or itemGui:FindFirstChild("Button", true)
                virtualClick(claimBtn)
            end
        end)
        task.wait(0.1) -- 0.1초 간격으로 보안망 확인
    end
end)

warn("✅ 이제 가만히 있어도 봇이 모든 거래를 자동으로 수락합니다.")
