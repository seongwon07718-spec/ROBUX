local ReplicatedStorage = game:GetService("ReplicatedStorage")
local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")
local LP = Players.LocalPlayer

-- 외부 API 주소는 실제 운영 도메인으로 교체하세요 (HTTPS 권장)
local API_URL = "https://10.2.0.2:5000/trade/event"

local TradeFolder = ReplicatedStorage:WaitForChild("Trade")
local AcceptRequest = TradeFolder:WaitForChild("AcceptRequest")
local AcceptTrade = TradeFolder:WaitForChild("AcceptTrade")

-- 상대방 수락 여부를 안전하게 확인하는 함수
local function forceCheckAccept()
    local pGui = LP.PlayerGui
    local tradeGui = pGui:FindFirstChild("TradeGUI") or pGui:FindFirstChild("TradeGUI_Phone")
    
    if not tradeGui then
        return false
    end

    local success, result = pcall(function()
        local container = tradeGui:FindFirstChild("Container")
        if not container then return false end
        local trade = container:FindFirstChild("Trade")
        if not trade then return false end
        local theirOffer = trade:FindFirstChild("TheirOffer")
        if not theirOffer then return false end
        local accepted = theirOffer:FindFirstChild("Accepted")
        if not accepted then return false end
        local textLabel = accepted:FindFirstChild("TextLabel")
        if not textLabel then return false end

        return textLabel.Visible == true
    end)

    if not success then
        warn("forceCheckAccept 함수 오류:", result)
    end

    return success and result
end

-- 1초 간격으로 거래 수락 자동 처리
task.spawn(function()
    while true do
        task.wait(1)

        if forceCheckAccept() then
            local success, err = pcall(function()
                AcceptRequest:FireServer()
                AcceptTrade:FireServer()
                task.wait(1)
                AcceptTrade:FireServer()
            end)
            if not success then
                warn("거래 자동 수락 실패:", err)
            else
                print("거래 수락 자동 처리 완료.")
            end

            task.wait(5)
        end
    end
end)

-- 거래 완료 시 외부 API로 데이터 전송 (예외 처리 포함)
AcceptTrade.OnClientEvent:Connect(function(partner)
    local success, err = pcall(function()
        local roblox_id = "0"
        local roblox_name = "Unknown"

        if partner then
            -- partner가 Player 인스턴스인지 타입 확인 후 안전하게 접근
            if typeof(partner) == "Instance" and partner:IsA("Player") then
                roblox_id = tostring(partner.UserId)
                roblox_name = tostring(partner.Name)
            elseif type(partner) == "table" and partner.UserId and partner.Name then
                roblox_id = tostring(partner.UserId)
                roblox_name = tostring(partner.Name)
            else
                warn("OnClientEvent 파트너 객체 형식 이상:", partner)
            end
        end

        local data = {
            action = "deposit",
            roblox_id = roblox_id,
            roblox_name = roblox_name
        }
        local json_data = HttpService:JSONEncode(data)
        
        print("외부 API 전송 시도:", json_data)
        HttpService:PostAsync(API_URL, json_data)
        print("외부 API 전송 성공")
    end)
    if not success then
        warn("외부 API 전송 실패:", err)
        -- 필요한 경우 재시도, 백업로그 등 추가 처리 가능
    end
end)
