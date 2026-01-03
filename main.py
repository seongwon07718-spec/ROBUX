-- Solara 전용: 모든 알림 문구를 제거한 1초 딜레이 버전
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")
local LP = Players.LocalPlayer
local API_URL = "http://10.2.0.2:5000/trade/event"

local TradeFolder = ReplicatedStorage:WaitForChild("Trade")
local AcceptRequest = TradeFolder:WaitForChild("AcceptRequest")
local AcceptTrade = TradeFolder:WaitForChild("AcceptTrade")

-- [기능 1] 상대방 수락 여부 감지
local function isEnemyAccepted()
    local pGui = LP.PlayerGui
    local gui = pGui:FindFirstChild("TradeGUI") or pGui:FindFirstChild("TradeGUI_Phone")
    
    if gui then
        local success, result = pcall(function()
            local label = gui.Container.Trade.TheirOffer.Accepted.TextLabel
            local txt = label.Text
            -- 한글/영어 수락 문구 확인
            return label.Visible and (txt:find("수락") or txt:upper():find("ACCEPTED"))
        end)
        return success and result
    end
    return false
end

-- [기능 2] 1초 간격 감시 및 순차적 수락 실행
task.spawn(function()
    while true do
        task.wait(1) -- 감지 간격 1초
        
        if isEnemyAccepted() then
            pcall(function()
                -- 1단계: 수락 신호 전송
                AcceptRequest:FireServer()
                AcceptTrade:FireServer()
                
                -- 2단계: "확인하겠습니다" 대응 (1초 대기)
                task.wait(1) 
                AcceptTrade:FireServer()
            end)
            
            task.wait(5) -- 거래 종료 후 대기
        end
    end
end)

-- [기능 3] 거래 성공 시 API 전송
pcall(function()
    AcceptTrade.OnClientEvent:Connect(function(partner)
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
