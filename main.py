-- [[ MM2 VIRTUAL CLICK AUTO-ACCEPT ]]
local LP = game.Players.LocalPlayer
local PlayerGui = LP:WaitForChild("PlayerGui")
local VirtualInputManager = game:GetService("VirtualInputManager")

print("🖱️ [System] 좌표 클릭 엔진 가동 - 로블록스 창을 띄워두세요!")

-- 1. 버튼 클릭 함수 (가상 마우스)
local function virtualClick(guiObject)
    local x = guiObject.AbsolutePosition.X + (guiObject.AbsoluteSize.X / 2)
    local y = guiObject.AbsolutePosition.Y + (guiObject.AbsoluteSize.Y / 55) -- 상단 바 오차 보정
    
    VirtualInputManager:SendMouseButtonEvent(x, y, 0, true, game, 0) -- 마우스 누름
    task.wait(0.05)
    VirtualInputManager:SendMouseButtonEvent(x, y, 0, false, game, 0) -- 마우스 뗌
end

-- 2. 메인 감시 및 클릭 엔진
task.spawn(function()
    local isClicking = false
    
    while task.wait(0.5) do
        pcall(function()
            -- 영상 실측 경로 적용
            local tradeGui = PlayerGui:FindFirstChild("TradeGUI")
            local tradeFrame = tradeGui and tradeGui:FindFirstChild("Trade")
            local container = tradeFrame and tradeFrame:FindFirstChild("Container")
            
            if container then
                -- 타이머 상태 확인 (Status 라벨의 숫자가 사라졌는지)
                local statusLabel = container.Trade.Status:FindFirstChild("Status")
                local statusText = statusLabel and statusLabel.Text or ""
                local hasTimer = statusText:find("%d")
                
                -- 상대방 수락 여부 확인
                local partnerStatus = container.TheirOffer:FindFirstChild("Status")
                local partnerAccepted = partnerStatus and (partnerStatus.Text:find("Accepted") or partnerStatus.Text:find("수락"))

                -- 조건 충족 시 실제 버튼 좌표 클릭
                if not hasTimer and partnerAccepted and not isClicking then
                    isClicking = true
                    
                    -- 수락 버튼(Accept/Confirm) 위치 찾기
                    local acceptBtn = container:FindFirstChild("Confirm") or container:FindFirstChild("Accept")
                    if acceptBtn then
                        print("🚀 조건 충족! 좌표 클릭 실행")
                        virtualClick(acceptBtn)
                        
                        -- 확인창(Confirm)이 뜨면 그것도 클릭
                        task.wait(0.5)
                        local confirmGui = PlayerGui:FindFirstChild("TradeConfirm")
                        if confirmGui and confirmGui.Visible then
                            virtualClick(confirmGui.Container.Accept)
                        end
                    end
                    
                    task.wait(3)
                    isClicking = false
                end
            end
        end)
    end
end)
