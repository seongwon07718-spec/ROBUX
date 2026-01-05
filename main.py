BASE_PATH = pathlib.Path(__file__).parent.resolve()

async def create_merged_gif(result_side, c_data, p_data, bet_id):
    # 사진 7번 파일명과 100% 일치하게 경로 설정
    base_gif_path = BASE_PATH / f"final_fix_{result_side}.gif"
    
    if not base_gif_path.exists():
        print(f"❌ 파일을 못찾음: {base_gif_path}")
        return None

    async with aiohttp.ClientSession() as session:
        async with session.get(c_data['thumb']) as r1, session.get(p_data['thumb']) as r2:
            c_img = Image.open(io.BytesIO(await r1.read())).convert("RGBA").resize((120, 120))
            p_img = Image.open(io.BytesIO(await r2.read())).convert("RGBA").resize((120, 120))

    base_gif = Image.open(str(base_gif_path))
    frames = []
    font = ImageFont.load_default()

    # 렉 최적화: 프레임 압축
    for frame in range(base_gif.n_frames):
        base_gif.seek(frame)
        canvas = base_gif.convert("RGBA")
        canvas.paste(c_img, (40, 150), c_img)
        canvas.paste(p_img, (canvas.width - 160, 150), p_img)
        frames.append(canvas.convert("P", palette=Image.ADAPTIVE))

    out_path = BASE_PATH / f"temp_{bet_id}.gif"
    frames[0].save(str(out_path), save_all=True, append_images=frames[1:], duration=40, loop=0, optimize=True)
    return str(out_path)
