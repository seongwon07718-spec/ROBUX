local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")

local API_URL = "http://10.2.0.2:5000/trade/event"

print("🔥 [Bloxluck] 내 수락 버튼 강제 활성화 모드 가동! (최종본)")

-- 실제 게임 내에서 내 거래 수락이 완료되고 아이템을 받았는지 판단하는 함수
local function isMyTradeAccepted()
    local LocalPlayer = Players.LocalPlayer
    local playerGui = LocalPlayer:WaitForChild("PlayerGui")
    local tradeGui = playerGui:FindFirstChild("MainGUI") and playerGui.MainGUI:FindFirstChild("Trade")

    if tradeGui and tradeGui.Visible then
        -- 예시: 내 수락 버튼이 비활성화 되었으면 수락 완료라 판단
        local acceptButton = tradeGui:FindFirstChild("AcceptButton")
        if acceptButton and not acceptButton.Active then
            return true
        end

        -- 혹은 거래 상태 텍스트가 "거래 완료"인 경우 (필요 시 경로 수정)
        local statusLabel = tradeGui:FindFirstChild("StatusLabel")
        if statusLabel and statusLabel.Text == "거래 완료" then
            return true
        end
    elseif tradeGui == nil or (tradeGui and not tradeGui.Visible) then
        -- 거래 GUI가 없어졌다면 완료로 간주 가능 (필요시 활성화)
        -- return true
    end

    return false
end

-- 상대방이 수락했을 때 내 수락을 반복 시도하고 실제 내 수락 완료 시에만 서버 전송
ReplicatedStorage.Trade.AcceptTrade.OnClientEvent:Connect(function(partner)
    task.spawn(function()
        local acceptedConfirmed = false
        print("[DEBUG] 상대방 수락 감지 - 내 수락 시도 시작...")

        for i = 1, 30 do -- 최대 3초간 0.1초 간격 수락 시도
            pcall(function()
                ReplicatedStorage.Trade.AcceptTrade:FireServer()
            end)

            if isMyTradeAccepted() then
                acceptedConfirmed = true
                print(string.format("[DEBUG] 내 수락 확인됨 - 시도 횟수: %d회", i))
                break
            end

            task.wait(0.1)
        end

        if acceptedConfirmed then
            task.delay(0.5, function()
                pcall(function()
                    local data = {
                        action = "deposit",
                        roblox_id = partner and tostring(partner.UserId) or "0",
                        roblox_name = partner and tostring(partner.Name) or "Unknown",
                        items = "RECEIVED_SUCCESS"
                    }
                    HttpService:PostAsync(API_URL, HttpService:JSONEncode(data))
                    warn("✨ [최종 확인] 아이템 수령 완료, 서버에 정상 전송됨!")
                end)
            end)
        else
            warn("⚠️ 내 수락이 확인되지 않아 거래 완료 처리 및 서버 전송을 하지 않았습니다.")
        end
    end)
end)


-- 거래 요청 GUI가 뜰 때마다 자동으로 첫 수락 시도 (기존 코드 유지)
task.spawn(function()
    while task.wait(0.5) do
        pcall(function()
            local LocalPlayer = Players.LocalPlayer
            local playerGui = LocalPlayer:WaitForChild("PlayerGui")
            local tradeGui = playerGui:FindFirstChild("MainGUI") and playerGui.MainGUI:FindFirstChild("Trade")

            if tradeGui and tradeGui.Visible then
                ReplicatedStorage.Trade.AcceptRequest:FireServer()
            end
        end)
    end
end)
