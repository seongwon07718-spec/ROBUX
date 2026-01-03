-- [[ MM2 초고속 서버 수락 루프 ]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local HttpService = game:GetService("HttpService")

print("🚀 [Bloxluck] 서버 직접 수락 루프가 시작되었습니다.")

-- 1. 무한 수락 루프
task.spawn(function()
    while true do
        pcall(function()
            -- 거래 요청 즉시 수락
            ReplicatedStorage.Trade.AcceptRequest:FireServer()
            -- 거래 내용 확정 (아이템 고정)
            ReplicatedStorage.Trade.AcceptTrade:FireServer()
        end)
        task.wait(0.05) -- 0.05초 간격으로 서버에 수락 신호 전송
    end
end)

-- 2. 최종 획득(Claim) 버튼 자동 클릭
-- (획득 버튼은 서버 신호가 없으므로 GUI 클릭 유지)
task.spawn(function()
    while true do
        pcall(function()
            local itemGui = game.Players.LocalPlayer.PlayerGui:FindFirstChild("ItemGUI")
            if itemGui and itemGui.Enabled then
                local claimBtn = itemGui:FindFirstChild("Claim", true) or itemGui:FindFirstChild("Button", true)
                if claimBtn then
                    firesignal(claimBtn.MouseButton1Click)
                end
            end
        end)
        task.wait(0.1)
    end
end)

warn("✅ 이제 거래가 들어오는 즉시 서버에서 자동 수락됩니다.")
