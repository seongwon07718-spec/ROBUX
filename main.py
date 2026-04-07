-- 선물 UI 버튼 찾아서 직접 클릭
local player = game:GetService("Players").LocalPlayer
local gui = player.PlayerGui

-- Gifting 페이지 찾기
local function findGiftButton()
    for _, v in pairs(gui:GetDescendants()) do
        if v:IsA("TextButton") or v:IsA("ImageButton") then
            if v.Name:lower():find("gift") or v.Name:lower():find("buy") then
                print(v:GetFullName(), v.Name)
            end
        end
    end
end

findGiftButton()
