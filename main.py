-- [[ 영상 데이터 분석 기반: 모바일 MM2 전용 자동화 ]] --
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")
local LocalPlayer = Players.LocalPlayer

-- 서버로 보낼 리모트 신호 (이건 동일함)
local AcceptRemote = ReplicatedStorage:WaitForChild("Trade"):WaitForChild("AcceptTrade")

-- [시각화 상태창]
local sg = Instance.new("ScreenGui", LocalPlayer.PlayerGui)
local label = Instance.new("TextLabel", sg)
label.Size = UDim2.new(0, 250, 0, 50)
label.Position = UDim2.new(0, 10, 0, 10)
label.Text = "🤖 봇 대기 중 (영상 경로 적용됨)"

task.spawn(function()
    while task.wait(0.5) do
        pcall(function()
            -- 영상 로그에서 확인된 모바일 전용 실제 경로 적용
            local mainGui = LocalPlayer.PlayerGui:FindFirstChild("MainGUI")
            local tradeContainer = mainGui.Lobby.Screens.Trading.Container
            local tradeFrame = tradeContainer:FindFirstChild("Trade")
            local requestFrame = tradeContainer:FindFirstChild("TradeRequest")

            -- 1. 들어오는 거래 요청 자동 수락
            if requestFrame and requestFrame.Visible then
                AcceptRemote:FireServer()
                label.Text = "✅ 거래 요청 수락함!"
            end

            -- 2. 거래창 안에서 1차/2차 자동 수락
            if tradeFrame and tradeFrame.Visible then
                label.Text = "📍 거래 감지! 수락 시작..."
                AcceptRemote:FireServer() -- 1차 수락

                -- 2026 보안 대기 시간 (5초)
                task.wait(5.1)

                -- 2차 최종 수락 (3번 연속 전송으로 확실히 처리)
                AcceptRemote:FireServer()
                task.wait(0.1)
                AcceptRemote:FireServer()
                task.wait(0.1)
                AcceptRemote:FireServer()
                
                label.Text = "✨ 최종 수락 완료!"
                repeat task.wait(1) until not tradeFrame.Visible
            else
                label.Text = "🤖 거래 대기 중..."
            end
        end)
    end
end)
