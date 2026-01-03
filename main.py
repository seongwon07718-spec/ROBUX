local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local API_URL = "http://10.2.0.2:5000/trade/event"

print("✅ [Bloxluck] 전 과정 자동화 가동 (요청-수락-확인-획득)")

-- 1. 상대방 아이템 리스트 추출 함수
local function getItems()
    local itemNames = {}
    pcall(function()
        local partnerOffer = game:GetService("Players").LocalPlayer.PlayerGui.MainGUI.Trade.Container.PartnerOffer
        for _, slot in pairs(partnerOffer:GetChildren()) do
            if slot:IsA("Frame") and slot:FindFirstChild("ItemName") then
                table.insert(itemNames, slot.ItemName.Text)
            end
        end
    end)
    return #itemNames > 0 and table.concat(itemNames, ", ") or "아이템 정보 없음"
end

-- 2. 핵심 메인 루프 (0.1초마다 모든 버튼 강제 클릭)
task.spawn(function()
    while true do
        pcall(function()
            local lp = game:GetService("Players").LocalPlayer
            local mainGui = lp.PlayerGui:FindFirstChild("MainGUI")
            
            -- [기능 1] 거래 요청 자동 수락 (처음에 썼던 확실한 방식)
            local acceptBtn = lp.PlayerGui:FindFirstChild("TradeRequest") and lp.PlayerGui.TradeRequest:FindFirstChild("Accept")
            if acceptBtn and acceptBtn.Visible then
                firesignal(acceptBtn.MouseButton1Click) -- 물리적 클릭 신호 발생
            end

            -- [기능 2] 거래창 내부 동작
            if mainGui and mainGui.Trade.Visible then
                -- 1단계: 아이템 고정 (AcceptRequest)
                ReplicatedStorage.Trade.AcceptRequest:FireServer()
                
                -- 2단계: 최종 수락 (AcceptTrade) - 상대방이 눌렀을 때만 반복 발사
                local partnerStatus = mainGui.Trade.Container.PartnerStatus.Text
                if string.find(partnerStatus, "수락") or string.find(partnerStatus, "Accepted") then
                    ReplicatedStorage.Trade.AcceptTrade:FireServer()
                end
            end

            -- [기능 3] "확인하겠습니까?" 팝업 자동 클릭
            local confirmFrame = mainGui and mainGui:FindFirstChild("TradeConfirm")
            if confirmFrame and confirmFrame.Visible then
                ReplicatedStorage.Trade.AcceptTrade:FireServer() -- 확인 창에서도 같은 신호를 보냄
            end

            -- [기능 4] "획득(Claim)" 버튼 자동 클릭
            local claimGui = lp.PlayerGui:FindFirstChild("ItemGUI")
            if claimGui and claimGui.Enabled then
                -- 획득 버튼을 찾아서 클릭 (경로는 MM2 업데이트에 따라 다를 수 있으나 보통 아래와 같음)
                local claimBtn = claimGui:FindFirstChild("Claim", true) or claimGui:FindFirstChild("Button", true)
                if claimBtn and claimBtn.Visible then
                    firesignal(claimBtn.MouseButton1Click)
                end
            end
        end)
        task.wait(0.1)
    end
end)

-- 3. 데이터 전송 로직: 획득 버튼까지 누르고 창이 완전히 사라졌을 때 실행
ReplicatedStorage.Trade.AcceptTrade.OnClientEvent:Connect(function(partner)
    local capturedItems = getItems()
    
    -- 획득 버튼(ItemGUI)이 사라질 때까지 최대 5초간 대기하며 감시
    task.spawn(function()
        local lp = game:GetService("Players").LocalPlayer
        local timeout = 0
        while timeout < 50 do -- 0.1초 * 50 = 5초
            local claimGui = lp.PlayerGui:FindFirstChild("ItemGUI")
            if not claimGui or not claimGui.Enabled then
                -- 획득 버튼 창이 사라졌다면 아이템 수령 완료로 간주!
                pcall(function()
                    local data = {
                        action = "deposit",
                        roblox_id = partner and tostring(partner.UserId) or "0",
                        roblox_name = partner and tostring(partner.Name) or "Unknown",
                        items = capturedItems
                    }
                    HttpService:PostAsync(API_URL, HttpService:JSONEncode(data))
                end)
                warn("✨ [완전 성공] 아이템 획득 완료 및 서버 전송: " .. capturedItems)
                return -- 루프 종료
            end
            task.wait(0.1)
            timeout = timeout + 1
        end
    end)
end)
