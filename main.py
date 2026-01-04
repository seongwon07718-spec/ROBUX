-- [[ UI 경로 추적기: 거래창을 열고 화면을 보세요 ]] --
local player = game.Players.LocalPlayer
local sg = Instance.new("ScreenGui", player.PlayerGui)
local label = Instance.new("TextLabel", sg)
label.Size = UDim2.new(0, 400, 0, 100)
label.Position = UDim2.new(0, 10, 0, 10)
label.BackgroundColor3 = Color3.new(0, 0, 0)
label.TextColor3 = Color3.new(0, 1, 0) -- 초록색 글씨
label.TextSize = 15
label.TextXAlignment = Enum.TextXAlignment.Left
label.Text = "거래창을 열면 경로가 여기에 표시됩니다..."

game:GetService("RunService").RenderStepped:Connect(function()
    local found = false
    -- PlayerGui 안의 모든 것을 뒤져서 'Trade' 단어가 들어간 UI를 찾습니다.
    for _, v in pairs(player.PlayerGui:GetDescendants()) do
        if v:IsA("Frame") and v.Visible and (v.Name:find("Trade") or v.Name:find("Accept")) then
            label.Text = "📍 찾은 경로: \n" .. v:GetFullName()
            found = true
            break
        end
    end
    if not found then label.Text = "거래창을 찾고 있습니다... (열어주세요)" end
end)

-- [[ 모든 UI 버튼 이름 출력 ]] --
local player = game.Players.LocalPlayer
print("--- [현재 로드된 모든 버튼 목록] ---")
for _, v in pairs(player.PlayerGui:GetDescendants()) do
    if v:IsA("TextButton") or v:IsA("ImageButton") then
        if v.Visible then
            print("버튼 이름: " .. v.Name .. " | 경로: " .. v:GetFullName())
        end
    end
end
print("---------------------------------")
