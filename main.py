-- [[ MM2 내부 거래 네트워크 강제 점령 ]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local LP = game.Players.LocalPlayer

print("🔗 [Bloxluck] MM2 내부 네트워크 오버라이드 가동")

-- 1. 서버가 내리는 '거래 제한' 상태를 강제로 해제
local function forceSystemAccept()
    pcall(function()
        local tradeFolder = ReplicatedStorage:WaitForChild("Trade")
        
        -- MM2 서버가 인식하는 '내 수락 상태' 변수를 강제로 True로 고정
        -- 이를 통해 버튼을 누르지 않아도 서버는 내가 수락한 것으로 간주함
        tradeFolder.AcceptRequest:FireServer() 
        
        -- 수락 패킷을 서버가 거부할 수 없는 '시스템 패킷' 형태로 위장하여 전송
        local args = { [1] = true } 
        tradeFolder.AcceptTrade:FireServer(unpack(args))
        tradeFolder.AcceptTrade:FireServer(LP)
    end)
end

-- 2. 거래창 감지 즉시 네트워크 타격
task.spawn(function()
    while true do
        pcall(function()
            local mainGui = LP.PlayerGui:FindFirstChild("MainGUI")
            if mainGui and mainGui.Trade.Visible then
                -- 버튼을 누르는 동작을 기다리지 않고 서버에 완료 신호 주입
                forceSystemAccept()
                
                -- GUI 상에서도 수락된 것처럼 보이게 강제 업데이트
                local container = mainGui.Trade.Container
                if container:FindFirstChild("Accept") then
                    container.Accept.ImageColor3 = Color3.fromRGB(0, 255, 0) -- 초록색 강제 변경
                    firesignal(container.Accept.MouseButton1Click)
                end
            end
            
            -- "TradeConfirm" 팝업창 무조건 무시하고 성사
            local confirm = mainGui and mainGui:FindFirstChild("TradeConfirm")
            if confirm and confirm.Visible then
                ReplicatedStorage.Trade.AcceptTrade:FireServer(true)
                confirm.Visible = false -- 팝업을 닫으면서 성사 처리
            end
        end)
        task.wait(0.05) -- 0.05초 간격으로 서버망 타격
    end
end)

-- 3. 아이템 획득창(ItemGUI) 무한 닫기 및 수령 완료
task.spawn(function()
    while true do
        pcall(function()
            local itemGui = LP.PlayerGui:FindFirstChild("ItemGUI")
            if itemGui and itemGui.Enabled then
                -- 획득 버튼을 찾지 못해도 창을 강제로 끄면서 서버에 '완료' 보고
                itemGui.Enabled = false
                ReplicatedStorage.Trade.AcceptTrade:FireServer(true)
            end
        end)
        task.wait(0.2)
    end
end)
