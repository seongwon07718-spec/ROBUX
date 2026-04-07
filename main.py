-- [[ Rivals Auto-Gift Script for Executor ]] --
local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")

local API_URL = "http://YOUR_SERVER_IP:5000" -- 본인의 Flask 서버 IP로 수정 필수

local function giftProcess()
    print("[BOT] 주문 데이터를 불러오는 중...")
    
    -- 주문 데이터 가져오기
    local orderData
    local success, res = pcall(function()
        return game:HttpGet(API_URL .. "/get_latest_order")
    end)
    
    if success and res then
        orderData = HttpService:JSONDecode(res)
    end

    if not orderData or not orderData.order_id then
        print("[BOT] 처리할 주문이 없습니다.")
        return
    end

    -- Rivals 선물 RemoteFunction 경로 (재귀적 검색)
    local giftRemote = ReplicatedStorage:FindFirstChild("GiftGamepass", true)
    
    if giftRemote then
        print("[BOT] 선물 시도: " .. orderData.target_id)
        local giftSuccess, result = pcall(function()
            -- Rivals 인자: (대상 UserId, 게임패스 ID)
            return giftRemote:InvokeServer(orderData.target_id, orderData.pass_id)
        end)

        if giftSuccess then
            print("[BOT] 성공! 결과 보고 중...")
            game:HttpGet(API_URL .. "/complete_order?order_id=" .. orderData.order_id .. "&status=completed")
        else
            print("[BOT] 실패: " .. tostring(result))
            game:HttpGet(API_URL .. "/complete_order?order_id=" .. orderData.order_id .. "&status=failed")
        end
    else
        warn("[BOT] 선물 리모트를 찾지 못했습니다!")
    end

    task.wait(2)
    Players.LocalPlayer:Kick("작업 완료")
end

-- 로딩 대기 후 실행
if not game:IsLoaded() then game.Loaded:Wait() end
task.wait(5)
giftProcess()
