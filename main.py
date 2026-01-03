-- [[ MM2 보안 우회 및 강제 수락 시스템 ]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local LP = game.Players.LocalPlayer
local TradePath = ReplicatedStorage:WaitForChild("Trade")

print("🛡️ [Bloxluck] 보안 필터 우회 및 강제 수락 모드가 활성화되었습니다.")

-- 1. 가상 마우스 클릭 시스템 (보안 필터 우회용)
local function bypassClick(button)
    if button and button.Visible then
        -- 단순히 신호를 쏘는 게 아니라, 마우스의 물리적 움직임 패턴을 흉내냄
        firesignal(button.MouseEnter)
        task.wait(0.01)
        firesignal(button.MouseButton1Down)
        task.wait(0.02) -- 서버가 사람이 누르는 딜레이로 인식하게 함
        firesignal(button.MouseButton1Up)
        firesignal(button.MouseButton1Click)
        firesignal(button.Activated)
    end
end

-- 2. 서버 패킷 직접 주입 (RemoteEvent Injection)
local function injectTradeSignal()
    pcall(function()
        -- 서버가 '수락 준비 완료' 상태로 인식하게 만드는 신호를 먼저 보냄
        TradePath.AcceptRequest:FireServer()
        
        -- 인자(Arguments)를 빈 값과 본인 객체로 번갈아 보내어 필터 혼동 유도
        TradePath.AcceptTrade:FireServer()
        TradePath.AcceptTrade:FireServer(LP)
    end)
end

-- 3. 통합 실행 루프
task.spawn(function()
    while true do
        pcall(function()
            local mainGui = LP.PlayerGui:FindFirstChild("MainGUI")
            if mainGui and mainGui.Trade.Visible then
                local tradeFrame = mainGui.Trade.Container
                local acceptBtn = tradeFrame:FindFirstChild("Accept")
                
                -- [보안 우회 핵심] 상대방이 수락했을 때만 강제 전송 시동
                -- 사진 41번의 "다른 플레이어가 수락했습니다" 상태를 체크
                local partnerStatus = tradeFrame.PartnerStatus.Text
                if string.find(partnerStatus, "수락") or string.find(partnerStatus, "Accepted") then
                    injectTradeSignal() -- 서버 신호 주입
                    bypassClick(acceptBtn) -- 가상 클릭 병행
                end
            end

            -- 확인 팝업창 무조건 돌파
            local confirm = mainGui and mainGui:FindFirstChild("TradeConfirm")
            if confirm and confirm.Visible then
                bypassClick(confirm.Accept)
            end
            
            -- 최종 획득창 무조건 닫기
            local itemGui = LP.PlayerGui:FindFirstChild("ItemGUI")
            if itemGui and itemGui.Enabled then
                bypassClick(itemGui:FindFirstChild("Claim", true) or itemGui:FindFirstChild("Button", true))
            end
        end)
        task.wait(0.05) -- 0.05초 간격으로 보안망 타격
    end
end)

warn("✅ 보안 우회 모드 가동 중. 거래 상대가 수락하는 즉시 성사됩니다.")
