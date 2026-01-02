local HttpService = game:GetService("HttpService")
local API_URL = "http://10.2.0.2:5000/trade/event" -- 사진 2번의 VPN 주소

print("✨ [Bloxluck] 모든 에러를 수정하고 가동을 시작합니다!")

-- 거래 수락 버튼을 직접 찾지 않고, 게임 시스템의 이벤트를 기다립니다.
game:GetService("ReplicatedStorage").Trade.AcceptTrade.OnClientEvent:Connect(function(partner, items)
    local data = {
        action = "deposit",
        roblox_id = tostring(partner.UserId),
        roblox_name = partner.Name,
        items = "아이템 감지됨"
    }
    
    -- 파이썬 서버로 데이터 전송 시도
    local success, response = pcall(function()
        return HttpService:PostAsync(API_URL, HttpService:JSONEncode(data))
    end)
    
    if success then
        print("✅ 서버 전송 성공! 디스코드를 확인하세요.")
    else
        print("❌ 전송 실패 (파이썬 서버가 켜져있나 확인하세요): " .. tostring(response))
    end
end)
