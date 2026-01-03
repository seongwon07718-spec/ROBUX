local Players = game:GetService("Players")
local LP = Players.LocalPlayer
local VirtualInputManager = game:GetService("VirtualInputManager")

print("--- [ 시스템 ] 버튼 강제 클릭 모드 활성화 ---")

local function getAcceptButton()
    local pGui = LP.PlayerGui
    -- 님의 로그에 찍힌 TradeGUI를 우선 탐색
    local tradeGui = pGui:FindFirstChild("TradeGUI")
    if not tradeGui then return nil end

    -- 모든 하위 객체 중 '수락' 텍스트를 가진 초록색 버튼 탐색
    for _, v in pairs(tradeGui:GetDescendants()) do
        if v:IsA("TextLabel") and (v.Text:find("수락") or v.Text:find("ACCEPT")) then
            -- 수락 문구 근처에 있는 실제 클릭 가능한 버튼을 찾음
            if v.Parent:IsA("TextButton") or v.Parent:IsA("ImageButton") then
                return v.Parent
            end
        end
    end
    return nil
end

-- 상대방이 수락했는지 체크하는 함수 (이미지 로그 기준 경로)
local function isEnemyAccepted()
    local success, result = pcall(function()
        -- 님의 이미지 로그 경로 정밀 반영: TheirOffer -> Accepted -> TextLabel
        local gui = LP.PlayerGui.TradeGUI.Container.Trade.TheirOffer.Accepted.TextLabel
        return gui.Visible and (gui.Text:find("ACCEPTED") or gui.Text:find("수락"))
    end)
    return success and result
end

task.spawn(function()
    while true do
        task.wait(0.1)
        if isEnemyAccepted() then
            local btn = getAcceptButton()
            if btn then
                -- 버튼의 화면 위치를 계산하여 실제 마우스 클릭 신호를 보냄 (리모트 차단 우회)
                local pos = btn.AbsolutePosition
                local size = btn.AbsoluteSize
                local centerX = pos.X + (size.X / 2)
                local centerY = pos.Y + (size.Y / 2) + 50 -- 상단 바 오차 보정

                -- 2회 연속 클릭 (확인 창까지 통과)
                for i = 1, 2 do
                    VirtualInputManager:SendMouseButtonEvent(centerX, centerY, 0, true, game, 1)
                    VirtualInputManager:SendMouseButtonEvent(centerX, centerY, 0, false, game, 1)
                    task.wait(0.1)
                end
                
                warn("⭐ 성공: 물리적 클릭으로 거래를 승인했습니다!")
                task.wait(5)
            end
        end
    end
end)
