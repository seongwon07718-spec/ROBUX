for _, v in pairs(game:GetDescendants()) do
    if v.Name:lower():find("cross") or v.Name:lower():find("gift") then
        print(v:GetFullName(), v.ClassName)
    end
end

local ok, result = pcall(function()
    return game:GetService("CrossExperienceGiftingService")
end)
print(ok, result)
