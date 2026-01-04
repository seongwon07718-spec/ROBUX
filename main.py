-- [[ 2026 MM2 모바일 전용: 상태 표시 + 무한 수락 ]] --
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")
local LocalPlayer = Players.LocalPlayer
local TradeRemote = ReplicatedStorage:WaitForChild("Trade"):WaitForChild("AcceptTrade")

-- [모바일 전용 상태 표시 UI 생성]
local screenGui = Instance.new("ScreenGui", LocalPlayer.PlayerGui)
local statusLabel = Instance.new("TextLabel", screenGui)
statusLabel.Size = UDim2.new(0, 200, 0, 50)
statusLabel.Position = UDim2.new(0, 10, 0, 10)
statusLabel.BackgroundColor3 = Color3.new(0, 0, 0)
statusLabel.BackgroundTransparency = 0.5
statusLabel.TextColor3 = Color3.new(1, 1, 1)
statusLabel.TextSize = 14
statusLabel.Text = "🤖 봇 대기 중..."

local function UpdateStatus(msg)
    statusLabel.Text = "🤖 " .. msg
end

task.spawn(function()
    while task.wait(0.3) do -- 서버 전송 주기를 더 빠르게 설정
        pcall(function()
            local tradeGui = LocalPlayer.PlayerGui:FindFirstChild("TradeGUI")
            local tradeFrame = tradeGui and tradeGui.Container:FindFirstChild("Trade")

            -- 1. 들어오는 모든 거래 요청 무한 수락 (서버로 계속 전송)
            TradeRemote:FireServer() 
            
            if tradeFrame and tradeFrame.Visible then
                UpdateStatus("거래 감지! 1차 수락 중...")
                TradeRemote:FireServer() -- 1차 수락

                -- 2. 2차 수락 대기 (모바일 안정권 5초)
                for i = 5, 1, -1 do
                    UpdateStatus("2차 수락 대기: " .. i .. "초")
                    task.wait(1)
                end

                -- 3. 2차 최종 수락 (확실하게 두 번 박기)
                UpdateStatus("최종 수락 전송!!")
                TradeRemote:FireServer()
                task.wait(0.1)
                TradeRemote:FireServer()
                
                repeat task.wait(1) until not tradeFrame.Visible
                UpdateStatus("거래 완료! 다음 대기 중...")
            else
                UpdateStatus("대기 중... (요청 자동 수락 활성)")
            end
        end)
    end
end)
