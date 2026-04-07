local player = game:GetService("Players").LocalPlayer
for _, v in pairs(player.PlayerGui:GetDescendants()) do
    if v:IsA("TextButton") or v:IsA("ImageButton") or v:IsA("Frame") then
        if v.Name:lower():find("gift") or v.Name:lower():find("offline") then
            print(v:GetFullName(), "|", v.ClassName, "|", v.Visible)
        end
    end
end
