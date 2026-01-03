-- [[ GLOBAL MM2 AUTO-TRADE SYSTEM - JAN 2026 ENHANCED ]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local LP = game.Players.LocalPlayer
local TradeRemote = ReplicatedStorage:WaitForChild("Trade")

print("📡 [System] MM2 모니터링 및 독립 수락 시스템 가동")

-- 1. CALLBACK HOOKING (나의 보안 검증만 자동 통과)
pcall(function()
    local getStatus = TradeRemote:WaitForChild("GetTradeStatus")
    if getStatus:IsA("RemoteFunction") then
        getStatus.OnClientInvoke = function()
            return true -- 서버가 '나'에게 물어볼 때만 true 응답
        end
    end
end)

-- 2. 거래 모니터링 및 개별 수락 로직
task.spawn(function()
    local lastPartnerItems = {} -- 중복 채팅 방지용

    while task.wait(0.3) do
        pcall(function()
            local mainGui = LP.PlayerGui:FindFirstChild("MainGUI")
            if mainGui and mainGui.Trade.Visible then
                local container = mainGui.Trade.Container
                
                -- [기능 1] 상대방 아이템 실시간 감지 및 출력
                local currentPartnerItems = {}
                for _, slot in pairs(container.PartnerSlots:GetChildren()) do
                    if slot:IsA("Frame") and slot.Visible and slot:FindFirstChild("ItemName") then
                        table.insert(currentPartnerItems, slot.ItemName.Text)
                    end
                end

                -- 새로운 아이템이 올라왔을 때만 출력
                if #currentPartnerItems > 0 and #currentPartnerItems ~= #lastPartnerItems then
                    print("💎 상대방이 아이템을 올림: " .. table.concat(currentPartnerItems, ", "))
                    lastPartnerItems = currentPartnerItems
                end

                -- [기능 2] 상대방 수락 상태 확인 (단순 모니터링)
                local partnerStatus = container.PartnerStatus.Text
                if string.find(partnerStatus, "Accepted") or string.find(partnerStatus, "수락됨") then
                    -- 주의: 여기서 상대방 신호를 가로채서 서버에 쏘는 것이 아니라, "상태"만 읽습니다.
                    print("⚠️ 상대방이 수락 버튼을 눌렀습니다. (내 수락 대기 중)")
                end

                -- [기능 3] 내 수락 패킷만 독립 전송 (상대방 신호와 혼선 방지)
                -- 중요: 상대방의 수락 여부와 상관없이 '나의 의사'만 서버에 전송합니다.
                TradeRemote.AcceptTrade:FireServer(true)
                TradeRemote.AcceptTrade:FireServer(LP)
                
                -- 확인 팝업창(TradeConfirm) 독립 돌파
                if mainGui:FindFirstChild("TradeConfirm") and mainGui.TradeConfirm.Visible then
                    TradeRemote.AcceptTrade:FireServer(true)
                end
            else
                lastPartnerItems = {} -- 거래 종료 시 초기화
            end
        end)
    end
end)

-- 3. 거래 요청 자동 수락
task.spawn(function()
    while task.wait(0.5) do
        pcall(function()
            TradeRemote.AcceptRequest:FireServer()
        end)
    end
end)
