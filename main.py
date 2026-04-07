local player = game:GetService("Players").LocalPlayer
local gui = player:WaitForChild("PlayerGui")
local MainGui = gui:WaitForChild("MainGui")
local MainFrame = MainGui:WaitForChild("MainFrame")

-- MainFrame 자식들 전부 출력
for _, v in pairs(MainFrame:GetChildren()) do
    print(v.Name, v.ClassName)
end
