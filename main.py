-- [[ MM2 REMOTE EVENT SNIFFER ]]
local MT = getrawmetatable(game)
local OldNameCall = MT.__namecall
setreadonly(MT, false)

print("🕵️ 리모트 감시 시작... 수락 버튼을 직접 눌러주세요.")

MT.__namecall = newcclosure(function(self, ...)
    local Method = getnamecallmethod()
    local Args = {...}

    -- Trade와 관련된 리모트 신호만 필터링해서 표시
    if (tostring(self) == "AcceptTrade" or tostring(self):find("Trade")) and Method == "FireServer" then
        print("------------------------------------------")
        print("📡 리모트 이름: " .. tostring(self))
        for i, v in pairs(Args) do
            print("🔢 인자[" .. i .. "]: " .. tostring(v) .. " (유형: " .. typeof(v) .. ")")
        end
        print("------------------------------------------")
    end
    return OldNameCall(self, ...)
end)
setreadonly(MT, true)
