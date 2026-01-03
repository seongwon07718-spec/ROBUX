# 옵션 설정 시 value를 명확히 지정
options = [
    discord.SelectOption(label="머더 미스테리", value="murder", ...),
    discord.SelectOption(label="입양하세요", value="adopt", ...)
]

# 데이터 키값도 영어로 통일 (오타 방지)
BOT_DATA = {
    "murder": [...],
    "adopt": [...]
}
