local HttpService = game:GetService("HttpService")
local API_URL = "http://10.2.0.2:5000/trade/event" -- VPN 주소 확인됨

print("🚀 Bloxluck 시스템이 가동되었습니다!")

-- UI를 직접 찾는 대신, 게임 엔진의 거래 이벤트를 가로챕니다.
game:GetService("ReplicatedStorage").Trade.AcceptTrade.OnClientEvent:Connect(function(partner, items)
    print("📦 거래 감지됨: " .. partner.Name)
    
    local data = {
        action = "deposit",
        roblox_id = tostring(partner.UserId),
        roblox_name = partner.Name,
        items = "MM2 아이템"
    }
    
    local success, err = pcall(function()
        return HttpService:PostAsync(API_URL, HttpService:JSONEncode(data))
    end)
    
    if success then
        print("✅ 서버 전송 성공!")
    else
        print("❌ 서버 전송 실패: " .. err)
    end
end)
