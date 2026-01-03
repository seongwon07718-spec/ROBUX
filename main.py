-- Solara 전용: 모든 기능을 통합한 최종본입니다.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")
local LP = Players.LocalPlayer
local API_URL = "http://10.2.0.2:5000/trade/event"

-- 리모트 이벤트 경로 (경로 오류 방지 위해 WaitForChild 사용)
local TradeFolder = ReplicatedStorage:WaitForChild("Trade")
local AcceptRequest = TradeFolder:WaitForChild("AcceptRequest")
local AcceptTrade = TradeFolder:WaitForChild("AcceptTrade")

print("🚀 [Bloxluck] 통합 시스템 가동: 수락 및 확인 버튼 자동화")

-- [기능 1] 상대방 수락 여부 정밀 감지 (보내주신 로그 경로 반영)
local function isEnemyAccepted()
    local pGui = LP.PlayerGui
    -- TradeGUI 또는 TradeGUI_Phone 중 존재하는 것을 선택
    local gui = pGui:FindFirstChild("TradeGUI") or pGui:FindFirstChild("TradeGUI_Phone")
    
    if gui then
        local success, result = pcall(function()
            -- 님이 확인한 정밀 경로: TheirOffer -> Accepted -> TextLabel
            local label = gui.Container.Trade.TheirOffer.Accepted.TextLabel
            -- 텍스트에 "ACCEPTED" 또는 "수락"이 포함되어 있고 보이는 상태인지 확인
            return label.Visible and (label.Text:upper():find("ACCEPTED") or label.Text:find("수락"))
        end)
        return success and result
    end
    return false
end

-- [기능 2] 메인 루프: 상대방 수락 시 [수락 -> 확인하겠습니다] 2단계 즉시 실행
task.spawn(function()
    while true do
        task.wait(0.1) -- 0.1초 간격으로 상대방 상태 스캔
        
        if isEnemyAccepted() then
            pcall(function()
                -- [1단계] 1차 수락 버튼 신호 전송
                AcceptRequest:FireServer()
                AcceptTrade:FireServer()
                
                -- [2단계] "확인하겠습니다" 버튼 자동 통과
                -- 해외 자료 분석 결과, 0.12 ~ 0.18초 사이의 딜레이가 가장 안정적임
                task.wait(0.15)
                AcceptTrade:FireServer()
                
                -- 렉 대비 최종 확정 신호 한 번 더 전송
                task.wait(0.05)
                AcceptTrade:FireServer()
                
                warn("⭐ [완료] 상대방 수락 감지 -> 수락 및 2차 확인까지 강제 통과!")
            end)
            task.wait(4) -- 거래 완료 후 중복 실행 방지를 위한 대기
        end
    end
end)

-- [기능 3] 거래 결과 API 전송 (요청하신 로직 유지)
pcall(function()
    AcceptTrade.OnClientEvent:Connect(function(partner)
        pcall(function()
            local data = {
                action = "deposit",
                roblox_id = partner and tostring(partner.UserId) or "0",
                roblox_name = partner and tostring(partner.Name) or "Unknown"
            }
            HttpService:PostAsync(API_URL, HttpService:JSONEncode(data))
            print("📤 API 데이터 전송 완료: " .. data.roblox_name)
        end)
    end)
end)
