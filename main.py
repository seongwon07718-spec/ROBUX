local player = game:GetService("Players").LocalPlayer
local MainFrame = player.PlayerGui.MainGui.MainFrame
local Pages = MainFrame:WaitForChild("Pages")

for _, v in pairs(Pages:GetChildren()) do
    print(v.Name, v.ClassName)
end
