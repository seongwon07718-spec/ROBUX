local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")

-- 외부 API 엔드포인트 URL
local API_URL = "http://10.2.0.2:5000/trade/event"

print("🔥 [Bloxluck] 내 수락 버튼 강제 활성화 모드 가동! (머더 미스터리 게임 맞춤 설명)")

--- 게임 내에서 실제 거래 수락이 완료되었는지 확인하는 함수
--- @return boolean tradeAccepted - 거래 수락이 성공적으로 이루어졌으면 true, 아니면 false
local function checkIfTradeAcceptedInGame()
    local LocalPlayer = Players.LocalPlayer
    local playerGui = LocalPlayer:WaitForChild("PlayerGui")
    
    -- [[!!!!! 튜어오오오옹님의 머더 미스터리 게임의 커스텀 거래 UI에 맞게 여기를 수정해주세요 !!!!!]]
    -- "머더 미스터리" 게임 내에 구현된 '거래 시스템'의 UI 요소를 찾아야 합니다.
    -- 예를 들어, 거래가 성공적으로 이루어졌을 때:
    -- 1. 거래창 자체가 사라지거나 (`tradeGui.Visible`이 false가 됨)
    -- 2. 거래창 내의 '수락' 버튼이 비활성화되거나 (`acceptButton.Active`가 false가 됨)
    -- 3. 거래 상태를 나타내는 텍스트가 "거래 완료" 또는 "아이템 획득" 등으로 변경되는지 확인해야 합니다.
    
    -- 아래 예시는 일반적인 GUI 경로입니다. 실제 경로는 게임마다 다를 수 있으니 직접 확인하셔야 합니다.
    local tradeGui = playerGui:FindFirstChild("YourCustomTradeGUI") -- 예: "TradeUI" 또는 "TradeScreen" 등
    
    if tradeGui then
        -- 튜어오오오옹님의 머더 미스터리 게임에서 거래 완료 후 UI 변화를 관찰하고 여기에 코드로 구현해야 합니다.
        
        -- 예시 1: 거래창이 닫히거나 숨겨지는 경우
        if not tradeGui.Visible then -- 거래창이 더 이상 보이지 않는다면 거래 완료로 간주
            return true
        end
        
        -- 예시 2: '수락' 버튼이 비활성화되는 경우
        local acceptButton = tradeGui:FindFirstChild("AcceptButtonName") -- 실제 버튼 이름으로 변경
        if acceptButton and not acceptButton.Active then
            return true
        end

        -- 예시 3: 거래 상태를 나타내는 텍스트가 변경되는 경우
        local statusText = tradeGui:FindFirstChild("StatusTextLabelName") -- 실제 텍스트 라벨 이름으로 변경
        if statusText and (statusText.Text == "거래 완료" or statusText.Text == "아이템 획득") then
            return true
        end
    end
    
    -- 위에서 어떤 조건도 만족하지 못하면 아직 거래가 완료되지 않았다고 판단합니다.
    return false
end

-- 1. 핵심: 상대방이 수락했을 때 내 수락을 '즉시' 그리고 '반복' 실행
ReplicatedStorage.Trade.AcceptTrade.OnClientEvent:Connect(function(partner)
    task.spawn(function()
        local myAcceptConfirmed = false
        print("상대방 수락 감지! 내 수락 시도 시작...")
        
        for i = 1, 30 do -- 수락 시도 횟수 및 시간 조정 (총 3초)
            pcall(function()
                ReplicatedStorage.Trade.AcceptTrade:FireServer()
            end)
            
            -- 수락 시도 후 게임 내에서 실제 수락이 되었는지 확인
            if checkIfTradeAcceptedInGame() then
                myAcceptConfirmed = true
                print(string.format("✅ [확인] %d번의 시도 끝에 게임 내에서 내 수락이 확인되었습니다! (머더 미스터리)", i))
                break -- 실제 수락 확인되었으면 더 이상 시도하지 않습니다.
            end
            task.wait(0.1)
        end

        -- 2. 실제 전송은 내 수락이 게임 내에서 확정되었을 때만 실행 (안정성 확보)
        if myAcceptConfirmed then
            -- 실제 수락 확인 후 0.5초 대기 (안정성을 위해 약간의 딜레이 유지)
            task.delay(0.5, function()
                pcall(function()
                    local data = {
                        action = "deposit",
                        roblox_id = partner and tostring(partner.UserId) or "0",
                        roblox_name = partner and tostring(partner.Name) or "Unknown",
                        items = "RECEIVED_SUCCESS"
                    }
                    HttpService:PostAsync(API_URL, HttpService:JSONEncode(data))
                    warn("✨ [최종 확인] 게임 내 수락 완료 및 데이터 전송 성공! (머더 미스터리)")
                end)
            end)
        else
            warn("❌ [경고] 게임 내에서 내 수락이 확인되지 않았습니다. 데이터 전송을 건너뛰었습니다.")
            warn("❗ checkIfTradeAcceptedInGame() 함수 내부 로직을 튜어오오오옹님의 머더 미스터리 게임에 맞춰 정확히 구현해야 합니다.")
        end
    end)
end)

-- 3. 첫 번째 거래 요청 수락 (이건 잘 된다고 하셨으니 유지)
task.spawn(function()
    while task.wait(0.5) do
        pcall(function()
            local LocalPlayer = Players.LocalPlayer
            local playerGui = LocalPlayer:WaitForChild("PlayerGui")
            -- 여기도 튜어오오오옹님의 머더 미스터리 게임의 커스텀 거래 UI에 맞게 경로를 수정해야 합니다.
            local tradeRequestGui = playerGui:FindFirstChild("YourCustomTradeRequestGUI") -- 예: "TradeRequestScreen" 등
            
            if tradeRequestGui and tradeRequestGui.Visible then
                ReplicatedStorage.Trade.AcceptRequest:FireServer()
                -- print("거래 요청 자동 수락 시도! (머더 미스터리)") -- 디버깅용
            end
        end)
    end
end)
