local player = game:GetService("Players").LocalPlayer
local MainFrame = player.PlayerGui.MainGui.MainFrame
local Pages = MainFrame:WaitForChild("Pages")

for _, v in pairs(Pages:GetDescendants()) do
    if v.Name:lower():find("gift") or v.Name:lower():find("shop") or v.Name:lower():find("store") then
        print(v:GetFullName(), v.ClassName)
    end
end
