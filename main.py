import random

pass_select = ui.Select(
    placeholder="게임패스를 선택해주세요",
    custom_id=f"pass_{selected_place_id}_{random.randint(1000, 9999)}"
)

proceed_btn = ui.Button(
    label="진행하기",
    style=discord.ButtonStyle.gray,
    emoji="<:success:1489875582874554429>",
    custom_id=f"proceed_{random.randint(1000, 9999)}"
)
