for _, v in pairs(game:GetDescendants()) do
    if v:IsA("RemoteFunction") or v:IsA("RemoteEvent") then
        if string.lower(v.Name):find("gift") or string.lower(v.Name):find("purchase") or string.lower(v.Name):find("buy") or string.lower(v.Name):find("pass") then
            print(v:GetFullName())
        end
    end
end
