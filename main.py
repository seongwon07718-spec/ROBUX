local HttpService = game:GetService("HttpService")
local API_URL = "http://10.2.0.2:5000/trade/event"

print("🚀 trade 시스템이 가동되었습니다!")

-- 인벤토리 UI를 직접 찾지 않고 시스템 이벤트를 감지합니다.
game:GetService("ReplicatedStorage").Trade.AcceptTrade.OnClientEvent:Connect(function(partner, items)
    local data = {
        action = "deposit",
        roblox_id = tostring(partner.UserId),
        roblox_name = partner.Name,
        items = "템 감지됨"
    }
    
    -- 서버 전송 시도
    local success, response = pcall(function()
        return HttpService:PostAsync(API_URL, HttpService:JSONEncode(data))
    end)
    
    if success then
        print("✅ 서버 전송 성공!")
    else
        print("❌ 전송 실패: " .. tostring(response))
    end
end) -- 여기서 괄호를 정확히 닫아주어야 사진 13의 에러가 사라집니다.
