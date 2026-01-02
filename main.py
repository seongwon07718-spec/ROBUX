local HttpService = game:GetService("HttpService")
local API_URL = "http://컴퓨터_아이피_주소:5000/trade/event"

-- 거래 완료 감지 함수
local function reportTrade(partnerId, partnerName, itemList, actionType)
    local data = {
        action = actionType,
        roblox_id = tostring(partnerId),
        roblox_name = partnerName,
        items = itemList
    }
    
    local success, err = pcall(function()
        HttpService:PostAsync(API_URL, HttpService:JSONEncode(data))
    end)
    
    if not success then warn("API 전송 실패: " .. err) end
end

-- MM2 자동 거래 수락 로직 (기존 메모리 조작 대신 이벤트 기반)
game:GetService("ReplicatedStorage").Trade.AcceptTrade.OnClientEvent:Connect(function(partner, items)
    -- 거래 수락 및 데이터 보고 로직 구현
    print("거래 감지됨: " .. partner.Name)
    reportTrade(partner.UserId, partner.Name, "MM2 Items List", "deposit")
end)
