embed = disnake.Embed(description=(
    f"**▸ 실시간 재고**\n"
    f"```{total_krw_value:,.0f}원```\n\n"
    f"**▸ 실시간 김프**\n"
    f"```{kimchi_premium:+.2f}%```\n"
    f"`2분 뒤 갱신됩니다`"
), color=0xFFFFFF)  # 흰색 배경

# 구분선 필드 추가 (이름을 특수문자나 공백으로 넣어 구분선처럼 활용)
embed.add_field(name="**ㅡ ㅡ ㅡ ㅡ ㅡ ㅡ ㅡ ㅡ ㅡ ㅡ ㅡ ㅡ ㅡ ㅡ ㅡ**", value="\u200b", inline=False)

# 임베드 푸터 추가
embed.set_footer(text="내역 조회는 정보 버튼을 눌려 확인 가능합니다")
