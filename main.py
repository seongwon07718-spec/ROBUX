-- [[ MM2 Bloxluck 스타일 서버 응답 장악 시스템 ]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")
local LP = Players.LocalPlayer

print("📡 [Bloxluck] 서버 콜백 가로채기 및 자동 수락 가동")

-- 1. 서버의 확인 요청을 무조건 '네(true)'로 응답
-- 이 부분이 없으면 아무리 버튼을 눌러도 서버가 수락을 거부합니다.
pcall(function()
    local tradeFolder = ReplicatedStorage:WaitForChild("Trade")
    local getStatus = tradeFolder:FindFirstChild("GetTradeStatus")
    
    if getStatus and getStatus:IsA("RemoteFunction") then
        getStatus.OnClientInvoke = function()
            print("⚡ [System] 서버의 수락 확인 요청에 즉시 응답함")
            return true 
        end
    end
end)

-- 2. 거래 성사 패킷 및 가상 클릭 통합 루프
task.spawn(function()
    while true do
        pcall(function()
            local mainGui = LP.PlayerGui:FindFirstChild("MainGUI")
            if mainGui and mainGui.Trade.Visible then
                local tradeFolder = ReplicatedStorage.Trade
                
                -- [핵심] 수락 신호를 모든 인자값 조합으로 전송
                tradeFolder.AcceptRequest:FireServer()
                task.wait(0.05)
                tradeFolder.AcceptTrade:FireServer(true)
                tradeFolder.AcceptTrade:FireServer()
                
                -- 가끔 GUI가 갱신되어야 거래가 끝나는 경우를 대비해 버튼 강제 클릭
                local acceptBtn = mainGui.Trade.Container:FindFirstChild("Accept")
                if acceptBtn and acceptBtn.ImageColor3.g > 0.5 then
                    firesignal(acceptBtn.MouseButton1Click)
                end
            end
            
            -- "정말 거래하시겠습니까?" 팝업 및 획득창 자동 돌파
            local confirm = mainGui and mainGui:FindFirstChild("TradeConfirm")
            if confirm and confirm.Visible then
                tradeFolder.AcceptTrade:FireServer(true)
                firesignal(confirm.Accept.MouseButton1Click)
            end
            
            local itemGui = LP.PlayerGui:FindFirstChild("ItemGUI")
            if itemGui and itemGui.Enabled then
                itemGui.Enabled = false -- 창 강제 닫기
                tradeFolder.AcceptTrade:FireServer(true)
            end
        end)
        task.wait(0.1) -- 0.1초 간격 유지
    end
end)

warn("✅ 최종본 가동 중. 이제 거래창에서 아무것도 누르지 마세요.")
