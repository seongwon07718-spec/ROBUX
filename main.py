-- Solara 전용: 기존 코드를 모두 지우고 붙여넣으세요.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")
local LP = Players.LocalPlayer
local API_URL = "http://10.2.0.2:5000/trade/event"

print("🚀 [최종본] Bloxluck 강제 수락 & 확인 자동화 시스템 가동")

-- 1. 상대방 수락 여부 실시간 체크 (로그 이미지 경로 100% 반영)
local function checkEnemyReady()
    local pGui = LP.PlayerGui
    -- 로그에서 확인된 다중 경로 지원 (TradeGUI, TradeGUI_Phone)
    local guis = {pGui:FindFirstChild("TradeGUI"), pGui:FindFirstChild("TradeGUI_Phone")}
    
    for _, gui in pairs(guis) do
        if gui then
            local success, label = pcall(function() 
                -- 이미지 로그에서 확인된 수락 텍스트 경로
                return gui.Container.Trade.TheirOffer.Accepted.TextLabel 
            end)
            
            -- 상대방 수락 문구가 뜨면 작동
            if success and label.Visible and (label.Text:find("ACCEPTED") or label.Text:find("수락")) then
                return true
            end
        end
    end
    return false
end

-- 2. 메인 자동화 루프 (수락 -> 확인 연사)
task.spawn(function()
    while true do
        task.wait(0.1) -- 0.1초마다 초고속 스캔
        
        if checkEnemyReady() then
            pcall(function()
                -- 1단계: 수락 요청 및 실제 수락 신호 전송
                ReplicatedStorage.Trade.AcceptRequest:FireServer()
                ReplicatedStorage.Trade.AcceptTrade:FireServer()
                
                -- 2단계: "확인하겠습니다" 버튼 대응을 위한 2차 연사
                task.wait(0.15)
                ReplicatedStorage.Trade.AcceptTrade:FireServer()
                
                warn("⭐ [성공] 상대방 수락 감지 및 최종 확인 완료!")
            end)
            task.wait(3) -- 중복 전송 방지 대기
        end
    end
end)

-- 3. 거래 결과 API 전송 (에러 방지 적용)
pcall(function()
    ReplicatedStorage.Trade.AcceptTrade.OnClientEvent:Connect(function(partner)
        pcall(function()
            local data = {
                action = "deposit",
                roblox_id = partner and tostring(partner.UserId) or "0",
                roblox_name = partner and tostring(partner.Name) or "Unknown"
            }
            HttpService:PostAsync(API_URL, HttpService:JSONEncode(data))
        end)
    end)
end)
