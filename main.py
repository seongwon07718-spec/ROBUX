-- [[ MM2 원격 이벤트 하이재킹 및 강제 승인 ]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local LP = game.Players.LocalPlayer

print("📡 [Bloxluck] 원격 이벤트 하이재킹 시스템 가동...")

-- 1. namecall 후킹을 통한 이벤트 가로채기
local mt = getrawmetatable(game)
local oldNamecall = mt.__namecall
setreadonly(mt, false)

mt.__namecall = newcclosure(function(self, ...)
    local method = getnamecallmethod()
    local args = {...}

    -- 거래 관련 신호(AcceptTrade)가 감지되면 데이터를 하이재킹
    if tostring(self) == "AcceptTrade" and method == "FireServer" then
        print("⚡ [Hijack] 거래 승인 신호가 보안을 우회하여 전송되었습니다.")
        -- 서버가 거부하지 못하도록 본인 객체를 포함한 최적화된 인자 전달
        return oldNamecall(self, LP) 
    end
    
    return oldNamecall(self, ...)
end)
setreadonly(mt, true)

-- 2. 강제 실행 루프 (하이재킹된 통로로 신호 주입)
task.spawn(function()
    local tradeRemote = ReplicatedStorage:WaitForChild("Trade"):WaitForChild("AcceptTrade")
    local acceptRequest = ReplicatedStorage:WaitForChild("Trade"):WaitForChild("AcceptRequest")
    
    while true do
        pcall(function()
            local mainGui = LP.PlayerGui:FindFirstChild("MainGUI")
            if mainGui and mainGui.Trade.Visible then
                -- 거래 요청 즉시 수락
                acceptRequest:FireServer()
                
                -- 하이재킹된 이벤트를 0.1초마다 강제 호출
                tradeRemote:FireServer()
                tradeRemote:FireServer(LP)
            end
            
            -- 2차 확인창 및 획득창 자동 돌파
            local confirm = mainGui and mainGui:FindFirstChild("TradeConfirm")
            if confirm and confirm.Visible then
                tradeRemote:FireServer(LP)
            end
            
            local itemGui = LP.PlayerGui:FindFirstChild("ItemGUI")
            if itemGui and itemGui.Enabled then
                -- 버튼을 누르는 대신 창을 강제로 닫고 완료 신호 전송
                itemGui.Enabled = false
                tradeRemote:FireServer(LP)
            end
        end)
        task.wait(0.1)
    end
end)

warn("✅ 하이재킹 준비 완료. 상대방이 수락을 누르면 즉시 거래가 성사됩니다.")
