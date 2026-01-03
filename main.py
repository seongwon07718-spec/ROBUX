local ReplicatedStorage = game:GetService("ReplicatedStorage")
local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")
local LP = Players.LocalPlayer

-- API_URL을 튜어오오오옹님이 사용하시는 도메인으로 변경했습니다. 필요에 따라 포트(5000)도 조정해 주세요.
local API_URL = "https://10.2.0.2:5000/trade/event" 

local TradeFolder = ReplicatedStorage:WaitForChild("Trade")
local AcceptRequest = TradeFolder:WaitForChild("AcceptRequest")
local AcceptTrade = TradeFolder:WaitForChild("AcceptTrade")

--- [기능] 상대방 수락 여부 정밀 체크 (모든 버튼 상태 전수 조사)
local function forceCheckAccept()
    local pGui = LP.PlayerGui
    local tradeGui = pGui:FindFirstChild("TradeGUI") or pGui:FindFirstChild("TradeGUI_Phone")
    
    if tradeGui then
        local success, result = pcall(function()
            -- GUI 경로를 FindFirstChild로 단계별로 확인하여 더 견고하게 만들었습니다.
            local container = tradeGui:FindFirstChild("Container")
            local trade = container and container:FindFirstChild("Trade")
            local theirOffer = trade and trade:FindFirstChild("TheirOffer")
            local accepted = theirOffer and theirOffer:FindFirstChild("Accepted")
            local textLabel = accepted and accepted:FindFirstChild("TextLabel")
            
            -- 텍스트 라벨이 존재하고 '보여지는' 상태라면 상대가 수락한 것으로 판단
            return textLabel and textLabel.Visible == true
        end)

        if not success then
            warn("거래 수락 GUI 확인 중 오류 발생:", result) -- 오류 메시지를 출력합니다.
        end
        return success and result
    end
    return false
end

--- [메인] 1초 간격 감시 및 순차 실행
task.spawn(function()
    while true do
        task.wait(1) -- 감지 간격 1초
        
        if forceCheckAccept() then
            local success, errorMessage = pcall(function()
                -- 1. 수락 버튼 단계 실행
                AcceptRequest:FireServer()
                AcceptTrade:FireServer()
                
                -- 2. 1초 대기 후 '확인하겠습니다' 단계 실행
                task.wait(1)
                AcceptTrade:FireServer()
            end)
            
            if not success then
                warn("자동 거래 수락 중 오류 발생:", errorMessage) -- 자동 수락 단계에서 오류 발생 시 경고
            else
                print("상대방 수락 감지 및 거래 수락 단계 완료.")
            end

            -- 거래 완료 처리를 위해 긴 대기 시간 부여
            task.wait(5)
        end
    end
end)

--- [기능] 외부 시스템(Bloxluck)으로 거래 결과 전송
-- pcall로 Connect를 감싸는 것보다 내부 로직에서 pcall을 사용하는 것이 더 일반적입니다.
AcceptTrade.OnClientEvent:Connect(function(partner)
    local success, errorMessage = pcall(function()
        local roblox_id = "0"
        local roblox_name = "Unknown"

        -- partner 변수에 대한 유효성 검사를 강화했습니다.
        -- Player 객체이거나, UserID와 Name을 포함하는 테이블일 경우 처리합니다.
        if partner then
            if typeof(partner) == "Instance" and partner:IsA("Player") then
                roblox_id = tostring(partner.UserId)
                roblox_name = tostring(partner.Name)
            elseif type(partner) == "table" and partner.UserId and partner.Name then
                roblox_id = tostring(partner.UserId)
                roblox_name = tostring(partner.Name)
            else
                warn("partner 객체 형식이 예상과 다릅니다:", partner)
            end
        end

        local data = {
            action = "deposit",
            roblox_id = roblox_id,
            roblox_name = roblox_name
        }
        local json_data = HttpService:JSONEncode(data)
        
        print("외부 API로 거래 데이터 전송 시도:", json_data)
        HttpService:PostAsync(API_URL, json_data)
        print("거래 데이터 전송 성공!")
    end)
    
    if not success then
        warn("Bloxluck 거래 결과 전송 실패:", errorMessage) -- HTTP 요청 실패 시 경고
        -- TODO: 여기에 HTTP 요청 실패 시 재시도 로직이나 다른 에러 핸들링을 추가할 수 있습니다.
    end
end)
