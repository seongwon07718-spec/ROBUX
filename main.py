-- [[ MM2 메타테이블 후킹 기반 자동 수락 시스템 ]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")
local LP = Players.LocalPlayer

print("🚀 [Bloxluck] 후킹 시스템이 활성화되었습니다.")

-- 1. 메타테이블 후킹 설정
local mt = getrawmetatable(game)
local oldNamecall = mt.__namecall
setreadonly(mt, false)

mt.__namecall = newcclosure(function(self, ...)
    local method = getnamecallmethod()
    local args = {...}

    -- 게임이 'AcceptTrade' 신호를 서버로 보내려고 할 때 가로챔
    if tostring(self) == "AcceptTrade" and method == "FireServer" then
        print("⚡ [Hook] 서버 수락 신호 감지 및 최적화 전송")
        -- 원래의 신호를 그대로 흘려보내되, 루프와 충돌하지 않게 처리
        return oldNamecall(self, unpack(args))
    end
    
    return oldNamecall(self, ...)
end)
setreadonly(mt, true)

-- 2. 강제 수락 루프 (후킹된 채널로 신호를 쏟아부음)
task.spawn(function()
    local tradeRemote = ReplicatedStorage:WaitForChild("Trade"):WaitForChild("AcceptTrade")
    local acceptRemote = ReplicatedStorage:WaitForChild("Trade"):WaitForChild("AcceptRequest")
    
    while true do
        pcall(function()
            -- 거래 요청이 오면 즉시 수락
            acceptRemote:FireServer()
            
            -- 후킹된 이벤트를 통해 강제 수락 신호 전송
            tradeRemote:FireServer()
        end)
        task.wait(0.1) -- 서버 과부하 방지를 위한 미세 지연
    end
end)

-- 3. 최종 획득(Claim) 버튼 자동 클릭
task.spawn(function()
    while true do
        pcall(function()
            local itemGui = LP.PlayerGui:FindFirstChild("ItemGUI")
            if itemGui and itemGui.Enabled then
                local claimBtn = itemGui:FindFirstChild("Claim", true) or itemGui:FindFirstChild("Button", true)
                if claimBtn then
                    -- 클릭 이벤트를 강제로 발생시킴
                    firesignal(claimBtn.MouseButton1Click)
                end
            end
        end)
        task.wait(0.5)
    end
end)

warn("✅ 후킹 완료. 이제 거래창이 뜨면 자동으로 서버 수락이 진행됩니다.")
