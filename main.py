-- [[ MM2 완전 자동 거래 수락 및 데이터 전송 스크립트 ]]
local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")
local LP = Players.LocalPlayer
local API_URL = "http://10.2.0.2:5000/trade/event" -- 사용자님의 파이썬 서버 주소

print("🚀 [Bloxluck] 머더 자동 수락 시스템이 활성화되었습니다.")

-- 1. 상대방 아이템 리스트 추출 함수
local function getPartnerItems()
    local itemNames = {}
    pcall(function()
        local mainGui = LP.PlayerGui:FindFirstChild("MainGUI")
        local partnerOffer = mainGui.Trade.Container.PartnerOffer
        for _, slot in pairs(partnerOffer:GetChildren()) do
            if slot:IsA("Frame") and slot:FindFirstChild("ItemName") then
                table.insert(itemNames, slot.ItemName.Text)
            end
        end
    end)
    return #itemNames > 0 and table.concat(itemNames, ", ") or "아이템 없음"
end

-- 2. 메인 자동화 루프 (0.1초 간격)
task.spawn(function()
    while true do
        pcall(function()
            local mainGui = LP.PlayerGui:FindFirstChild("MainGUI")
            
            -- [단계 1] 거래 요청 팝업 자동 수락
            local requestGui = LP.PlayerGui:FindFirstChild("TradeRequest")
            if requestGui and requestGui.Enabled then
                local acceptBtn = requestGui:FindFirstChild("Accept", true)
                if acceptBtn then firesignal(acceptBtn.MouseButton1Click) end
            end

            -- [단계 2] 거래창 내부 수락 로직
            if mainGui and mainGui.Trade.Visible then
                -- 아이템 고정 및 기본 수락
                ReplicatedStorage.Trade.AcceptRequest:FireServer()
                
                -- 상대방이 수락했다면 나도 최종 수락 강제 실행
                local partnerStatus = mainGui.Trade.Container.PartnerStatus.Text
                if string.find(partnerStatus, "수락") or string.find(partnerStatus, "Accepted") then
                    ReplicatedStorage.Trade.AcceptTrade:FireServer()
                end
            end

            -- [단계 3] "확인하겠습니까?" 팝업 돌파
            local confirmGui = mainGui and mainGui:FindFirstChild("TradeConfirm")
            if confirmGui and confirmGui.Visible then
                ReplicatedStorage.Trade.AcceptTrade:FireServer()
            end

            -- [단계 4] 최종 "획득(Claim)" 버튼 자동 클릭
            local itemGui = LP.PlayerGui:FindFirstChild("ItemGUI")
            if itemGui and itemGui.Enabled then
                local claimBtn = itemGui:FindFirstChild("Claim", true) or itemGui:FindFirstChild("Button", true)
                if claimBtn then firesignal(claimBtn.MouseButton1Click) end
            end
        end)
        task.wait(0.1)
    end
end)

-- 3. 거래 완료 감지 및 파이썬 서버 전송
ReplicatedStorage.Trade.AcceptTrade.OnClientEvent:Connect(function(partner)
    local items = getPartnerItems()
    task.wait(1) -- 획득 처리 시간 대기
    
    local mainGui = LP.PlayerGui:FindFirstChild("MainGUI")
    local itemGui = LP.PlayerGui:FindFirstChild("ItemGUI")
    
    -- 거래창과 획득창이 모두 닫혔을 때만 성공으로 간주
    if (not mainGui.Trade.Visible) and (not itemGui.Enabled) then
        pcall(function()
            HttpService:PostAsync(API_URL, HttpService:JSONEncode({
                action = "deposit",
                roblox_id = tostring(partner.UserId),
                roblox_name = tostring(partner.Name),
                items = items
            }))
        end)
        warn("✅ 거래 완료 보고 성공: " .. items)
    end
end)
