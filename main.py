-- [[ MM2 2026 AUTO TRADE BOT - 2nd Confirm & Webhook ]] --

local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Player = game.Players.LocalPlayer
local WebhookURL = "여기에_디스코드_웹훅_주소_입력"

-- 1. 최신 리모트 경로 탐색 (2026년 가변 경로 대응)
local TradeRemote = ReplicatedStorage:FindFirstChild("TradeAPI", true) or ReplicatedStorage:FindFirstChild("TradeEvent", true)

-- 2. 데이터 전송 함수 (유저 이름, 아이템 리스트)
local function sendTradeLog(targetName, items)
    local data = {
        ["embeds"] = {{
            ["title"] = "✅ 거래 완료 리포트",
            ["description"] = "**" .. targetName .. "** 님과 거래를 마쳤습니다.",
            ["fields"] = {
                {["name"] = "획득한 아이템", ["value"] = items, ["inline"] = false}
            },
            ["color"] = 5814783
        }}
    }
    pcall(function()
        HttpService:PostAsync(WebhookURL, HttpService:JSONEncode(data))
    end)
end

-- 3. 거래 ID 및 아이템 정보 추출 후 수락 로직
task.spawn(function()
    while task.wait(0.5) do
        pcall(function()
            local mainGui = Player.PlayerGui:FindFirstChild("MainGUI")
            local tradeGui = mainGui and mainGui:FindFirstChild("Trade")
            
            if tradeGui and tradeGui.Visible then
                -- 거래 상대방 이름 및 아이템 텍스트 추출
                local targetUser = tradeGui.Container.Target.PlayerName.Text
                local receivedItems = tradeGui.Container.Target.Offer.Items.Text -- 실제 GUI 구조에 따라 수정 필요
                local tradeID = tradeGui:GetAttribute("TradeID") -- 2026년 방식: 속성값에 ID 저장

                -- 1차 수락 (Accept)
                TradeRemote:FireServer("AcceptTrade", tradeID)
                
                -- 서버 검증을 위한 딜레이 (너무 빠르면 킥당함)
                task.wait(2.5) 
                
                -- 2차 최종 확인 (Confirm)
                TradeRemote:FireServer("ConfirmTrade", tradeID)
                
                -- 로그 전송
                sendTradeLog(targetUser, receivedItems)
                print("거래 수락 및 로그 전송 완료: " .. targetUser)
                
                -- 거래가 끝날 때까지 대기
                repeat task.wait(1) until not tradeGui.Visible
            end
            
            -- 들어오는 요청 자동 수락
            TradeRemote:FireServer("AcceptRequest")
        end)
    end
end)
