-- [[ MM2 UI Path Finder & Logger ]]
local LP = game.Players.LocalPlayer
local PlayerGui = LP:WaitForChild("PlayerGui")

print("------------------------------------------")
print("🔎 MM2 UI 구조 정밀 스캐닝 시작...")

-- 특정 문구(예: "제안", "수락", "Trade")가 포함된 UI를 찾는 함수
local function scanUI(parent, depth)
    depth = depth or 0
    local spacing = string.rep("  ", depth)
    
    for _, obj in pairs(parent:GetChildren()) do
        -- 가시성이 있는 UI 위주로 체크
        if obj:IsA("GuiObject") then
            -- 로그창에 이름과 경로 출력
            print(spacing .. "📍 이름: " .. obj.Name .. " | 클래스: " .. obj.ClassName .. " | 보임: " .. tostring(obj.Visible))
            
            -- 텍스트가 있는 경우 내용도 출력 (수락 버튼이나 아이템 이름 찾기용)
            if obj:IsA("TextLabel") or obj:IsA("TextButton") then
                print(spacing .. "   📝 텍스트 내용: [" .. obj.Text .. "]")
            end
            
            -- 하위 계층으로 더 깊이 탐색
            scanUI(obj, depth + 1)
        end
    end
end

-- 1. MainGUI 내의 모든 구조 출력 (거래창이 이 안에 있을 확률 99%)
if PlayerGui:FindFirstChild("MainGUI") then
    print("✅ MainGUI 발견! 구조를 분석합니다...")
    scanUI(PlayerGui.MainGUI)
else
    print("❌ MainGUI를 찾을 수 없습니다. 전체 PlayerGui를 스캔합니다.")
    scanUI(PlayerGui)
end

print("🔎 스캐닝 종료. 로그창(F9)의 내용을 확인하세요.")
print("------------------------------------------")
