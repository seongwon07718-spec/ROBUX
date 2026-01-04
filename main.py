-- [[ 2026 MM2 무한 리모트 스팸 (초단순 버전) ]] --
local TradeRemote = game:GetService("ReplicatedStorage"):WaitForChild("Trade"):WaitForChild("AcceptTrade")

print("🔥 무한 수락 신호 전송 시작! (UI 체크 없음)")

-- 화면에 작동 중인지 표시해주는 작은 글자 (모바일 확인용)
local sg = Instance.new("ScreenGui", game:GetService("Players").LocalPlayer.PlayerGui)
local txt = Instance.new("TextLabel", sg)
txt.Size = UDim2.new(0, 200, 0, 30)
txt.Position = UDim2.new(0, 10, 0, 10)
txt.Text = "RUNNING: Accept Spammer"
txt.BackgroundTransparency = 0.5

task.spawn(function()
    while true do
        -- 서버에 수락 신호를 무한 반복해서 보냄
        -- pcall은 에러가 나도 스크립트가 멈추지 않게 방어해줍니다.
        pcall(function()
            TradeRemote:FireServer()
        end)
        
        -- 너무 빠르면 킥당할 수 있으니 아주 미세한 간격을 둡니다.
        task.wait(0.2) 
    end
end)
