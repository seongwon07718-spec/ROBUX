local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local LP = Players.LocalPlayer

-- 서버 수락 이벤트
local AcceptRemote = ReplicatedStorage:WaitForChild("Trade"):WaitForChild("AcceptTrade")

print("--- [최종] MM2 자동 수락 & 확인 시스템 가동 ---")

-- 1. 상대방이 수락했는지 체크 (로그 분석 경로 반영)
local function isEnemyAccepted()
    local pGui = LP.PlayerGui
    -- 로그에 확인된 모든 GUI 후보군 탐색
    local guis = {pGui:FindFirstChild("TradeGUI"), pGui:FindFirstChild("TradeGUI_Phone"), pGui:FindFirstChild("MainGUI")}
    
    for _, gui in pairs(guis) do
        if gui then
            -- 로그 정밀 경로: TheirOffer.Accepted.TextLabel
            local success, label = pcall(function() 
                return gui.Container.Trade.TheirOffer.Accepted.TextLabel 
            end)
            
            if success and label.Visible and (label.Text:find("ACCEPTED") or label.Text:find("수락")) then
                return true
            end
        end
    end
    return false
end

-- 2. "확인하겠습니다" 또는 최종 수락 버튼을 눌러주는 함수
local function clickConfirmButton()
    local pGui = LP.PlayerGui
    -- 화면 전체에서 'ACCEPT' 또는 'CONFIRM' 문구가 있는 버튼을 찾아 직접 클릭 신호 전송
    for _, v in pairs(pGui:GetDescendants()) do
        if v:IsA("TextLabel") and v.Visible then
            local txt = v.Text:upper()
            if txt:find("ACCEPT") or txt:find("CONFIRM") or txt:find("수락") or txt:find("확인") then
                local btn = v:FindFirstAncestorOfClass("TextButton") or v:FindFirstAncestorOfClass("ImageButton")
                if btn and btn.Visible then
                    -- 리모트 이벤트 전송 (마우스 클릭보다 빠름)
                    AcceptRemote:FireServer()
                    return true
                end
            end
        end
    end
    return false
end

-- 메인 실행 루프
task.spawn(function()
    while true do
        task.wait(0.1) -- 0.1초마다 감시
        
        if isEnemyAccepted() then
            -- 1단계: 수락 신호 전송
            AcceptRemote:FireServer()
            
            -- 2단계: "확인하겠습니다" 버튼 대응 (잠시 대기 후 연속 전송)
            task.wait(0.2)
            clickConfirmButton()
            AcceptRemote:FireServer()
            
            warn("⭐ 시스템: 상대방 수락 감지 -> 1차 수락 및 2차 확인 완료!")
            task.wait(4) -- 거래 종료 후 중복 방지 대기
        end
    end
end)
