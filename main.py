-- Gift Ticket 보유 여부 확인
local Remotes = game:GetService("ReplicatedStorage"):WaitForChild("Remotes")
local RequestGifting = Remotes:WaitForChild("Misc"):WaitForChild("RequestGiftingDetails")

-- 반환값 자세히 출력
local ok, result = pcall(function()
    return RequestGiftingDetails:InvokeServer("8514281248")  
end)
print("ok:", ok)
print("result type:", type(result))
print("result:", result)

-- Gift Ticket 관련 UI 확인
local player = game:GetService("Players").LocalPlayer
for _, v in pairs(player.PlayerGui:GetDescendants()) do
    if v.Name:lower():find("ticket") or v.Name:lower():find("gift") then
        print(v:GetFullName())
    end
end
