-- [[ MM2 UI EXACT PATH FINDER ]]
local LP = game.Players.LocalPlayer
local PlayerGui = LP:WaitForChild("PlayerGui")

print("------------------------------------------")
print("🔍 [System] 거래 관련 핵심 경로 추적 시작...")

-- 화면에 보이고 'Trade'나 'Container' 단어가 포함된 것만 필터링
local function findExactPath(parent)
    for _, obj in pairs(parent:GetDescendants()) do
        if obj:IsA("GuiObject") and obj.Visible == true then
            -- 수락 버튼으로 의심되는 객체 찾기
            if obj.Name:lower():find("accept") or obj.Name:lower():find("confirm") then
                print("✅ [수락 버튼 경로]: " .. obj:GetFullName())
            end
            
            -- 아이템 슬롯으로 의심되는 객체 찾기
            if obj.Name:lower():find("slot") or obj.Name:lower():find("item") then
                print("📦 [아이템 슬롯 경로]: " .. obj:GetFullName())
            end

            -- 상대방 이름 레이블 찾기
            if obj:IsA("TextLabel") and (obj.Text:find("님") or obj.Text:find("'s")) then
                print("👤 [상대방 이름 경로]: " .. obj:GetFullName())
            end
        end
    end
end

-- 10초 동안 1초 간격으로 스캔 (그 사이에 거래창을 열어두세요)
task.spawn(function()
    for i = 1, 10 do
        print("🔎 스캔 중... (" .. i .. "/10)")
        findExactPath(PlayerGui)
        task.wait(1)
    end
    print("🔚 스캔 종료. 위 경로들을 확인하세요.")
end)
