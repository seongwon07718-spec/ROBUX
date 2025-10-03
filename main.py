main.py

import os, json, time, re, statistics, threading, hashlib, asyncio, base64, contextlib, sys
import discord
from discord import app_commands
from discord.ext import commands
from fastapi import FastAPI, Request
import uvicorn

# playwright 체크
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright, TimeoutError as PwTimeout
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False

# child watcher 방어
try:
    if sys.platform != "win32":
        loop = asyncio.get_event_loop()
        if hasattr(asyncio, "get_child_watcher"):
            try:
                asyncio.get_child_watcher()
            except NotImplementedError:
                from asyncio import SafeChildWatcher, set_child_watcher
                set_child_watcher(SafeChildWatcher())
except Exception:
    pass

# ===== 환경 =====
GUILD_ID = int(os.getenv("GUILD_ID", "1419200424636055592"))
GUILD = discord.Object(id=GUILD_ID)

GRAY = discord.Color.from_str("#808080")
RED = discord.Color.red()
GREEN = discord.Color.green()
ORANGE = discord.Color.orange()
PINK = discord.Color.from_str("#ff5ea3")

# 이모지
EMJ_NOTICE   = "<:Announcement:1423544323735027763>"
EMJ_CHARGE   = "<a:Card_Black:1423544325597560842>"
EMJ_INFO     = "<:saknagkang_00000:1371042122345484353>"
EMJ_BUY      = "<:Nitro:1423517143730749490>"
EMJ_TOSS     = "<:TOSS:1423544803559342154>"
EMJ_CULTURE  = "<:1200x630wa:1423544804721164370>"
EMJ_COIN     = "<:bitcoin:1423544805975265374>"
EMJ_APPROVE  = "<a:1209511710545813526:1421430914373779618>"
EMJ_DECLINE  = "<a:1257004507125121105:1421430917049749506>"
EMJ_HEART    = "💌"

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ===== DB =====
DB_PATH = "data.json"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "KBRIDGE_9f8a1c2b0e4a4a7f")
_db_lock = threading.Lock()

def _default_db():
    return {
        "categories": [],
        "products": [],
        "logs": {
            "purchase": {"enabled": False, "target_channel_id": None},
            "review":   {"enabled": False, "target_channel_id": None},
            "admin":    {"enabled": False, "target_channel_id": None},
            "secure":   {"enabled": False, "target_channel_id": None}
        },
        "payments": {"bank": False, "coin": False, "culture": False},
        "balances": {},
        "points": {},
        "orders": {},
        "account": {"bank": "", "number": "", "holder": ""},
        "bans": {},
        "reviews": {},
        "purchases_sent": {},
        "topups": {"requests": [], "receipts": []},
        "culture_accounts": {}  # {gid:{uid:{idEnc,pwEnc,options,cookies[],cookiesAt}}}
    }

def db_load():
    if not os.path.exists(DB_PATH):
        return _default_db()
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return _default_db()
    base=_default_db()
    for k,v in base.items():
        data.setdefault(k,v)
    def _intmap(d):
        out={}
        if isinstance(d, dict):
            for k,v in d.items():
                try: out[str(k)] = int(v)
                except: out[str(k)] = 0
        return out
    data["balances"] = {str(g): _intmap(u) for g,u in data.get("balances",{}).items()}
    data["points"]   = {str(g): _intmap(u) for g,u in data.get("points",{}).items()}
    for k in ("bank","number","holder"):
        data["account"][k] = str(data["account"].get(k,""))
    data["topups"].setdefault("requests", [])
    data["topups"].setdefault("receipts", [])
    data.setdefault("purchases_sent", {})
    data.setdefault("culture_accounts", {})
    return data

def db_save():
    with _db_lock:
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(DB, f, ensure_ascii=False, indent=2)

DB = db_load()

# ===== 유틸 =====
CUSTOM_EMOJI_RE = re.compile(r'^<(?P<anim>a?):(?P<name>[A-Za-z0-9_]+):(?P<id>\d+)>$')
def parse_partial_emoji(text: str):
    if not text: return None
    m = CUSTOM_EMOJI_RE.match(text.strip())
    if not m: return None
    try:
        return discord.PartialEmoji(name=m.group("name"), id=int(m.group("id")), animated=(m.group("anim")=="a"))
    except:
        return None

def safe_emoji(raw: str | None):
    pe = parse_partial_emoji(raw or "")
    return pe if pe else None

def _now(): return int(time.time())

def set_v2(e: discord.Embed):
    try: e.set_author(name="")
    except: pass
    try: e.set_footer(text="")
    except: pass
    return e

def star_bar(avg: float | None) -> str:
    if avg is None: return "평점 없음"
    n = max(1, min(int(round(avg)), 5))
    return "⭐️"*n

def product_avg_stars(p: dict) -> str:
    ratings = p.get("ratings", [])
    avg = round(statistics.mean(ratings), 1) if ratings else None
    return star_bar(avg)

def category_avg_stars(cat_name: str) -> str:
    ps = [p for p in DB["products"] if p["category"]==cat_name and p.get("ratings")]
    if not ps: return "평점 없음"
    all_r=[]
    for p in ps: all_r += p.get("ratings", [])
    if not all_r: return "평점 없음"
    avg = round(statistics.mean(all_r), 1)
    return star_bar(avg)

def ban_is_blocked(gid: int, uid: int) -> bool:
    return bool(DB["bans"].get(str(gid), {}).get(str(uid), False))

def bal_get(gid: int, uid: int) -> int:
    return DB["balances"].get(str(gid), {}).get(str(uid), 0)

def bal_set(gid: int, uid: int, val: int):
    DB["balances"].setdefault(str(gid), {})
    DB["balances"][str(gid)][str(uid)] = int(val); db_save()

def bal_add(gid: int, uid: int, amt: int):
    bal_set(gid, uid, bal_get(gid, uid) + max(0, int(amt)))

def bal_sub(gid: int, uid: int, amt: int):
    bal_set(gid, uid, bal_get(gid, uid) - max(0, int(amt)))

def pt_get(gid: int, uid: int) -> int:
    return DB["points"].get(str(gid), {}).get(str(uid), 0)

def orders_get(gid: int, uid: int):
    return DB.get("orders", {}).get(str(gid), {}).get(str(uid), [])

def orders_add(gid: int, uid: int, product: str, qty: int):
    DB.setdefault("orders", {}).setdefault(str(gid), {}).setdefault(str(uid), []).append(
        {"product": product, "qty": int(qty), "ts": _now()}
    ); db_save()

def prod_get(name: str, category: str):
    return next((p for p in DB["products"] if p["name"]==name and p["category"]==category), None)

def prod_list_by_cat(category: str):
    return [p for p in DB["products"] if p["category"]==category]

def prod_list_all():
    return list(DB["products"])

def prod_upsert(name: str, category: str, price: int, emoji_raw: str = "", desc: str = ""):
    p = prod_get(name, category)
    if p:
        p.update({"price": int(max(0, price)), "emoji_raw": emoji_raw, "desc": desc})
    else:
        DB["products"].append({
            "name": name, "category": category, "price": int(max(0, price)),
            "stock": 0, "items": [], "emoji_raw": emoji_raw, "ratings": [],
            "sold_count": 0, "desc": desc
        })
    db_save()

def prod_delete(name: str, category: str):
    DB["products"] = [p for p in DB["products"] if not (p["name"]==name and p["category"]==category)]
    db_save()

# ===== 로그 채널 =====
def get_log_channel(guild: discord.Guild, key: str) -> discord.TextChannel | None:
    cfg = DB["logs"].get(key) or {}
    if not cfg.get("enabled") or not cfg.get("target_channel_id"): return None
    ch = guild.get_channel(int(cfg["target_channel_id"]))
    return ch if isinstance(ch, discord.TextChannel) else None

async def send_log_embed(guild: discord.Guild, key: str, embed: discord.Embed):
    ch = get_log_channel(guild, key)
    if not ch: return False
    try:
        await ch.send(embed=embed); return True
    except: return False

async def send_log_text(guild: discord.Guild, key: str, text: str):
    ch = get_log_channel(guild, key)
    if not ch: return False
    try:
        await ch.send(text); return True
    except: return False

# ===== 구매/후기/DM =====
def emb_purchase_log(user: discord.User, product: str, qty: int):
    return set_v2(discord.Embed(
        title="구매로그",
        description=f"{user.mention}님 {product} {qty}개\n구매 감사합니다 후기 작성 부탁드립니다:gift_heart:",
        color=GRAY
    ))

def emb_review_full(product: str, stars: int, content: str):
    line="ㅡ"*18
    return set_v2(discord.Embed(
        title="구매 후기",
        description=f"**구매제품** : {product}\n**별점** : {'⭐️'*max(1,min(stars,5))}\n{line}\n{content}\n{line}",
        color=GRAY
    ))

def emb_purchase_dm(product: str, qty: int, price: int, items: list[str]):
    line="ㅡ"*18
    vis=items[:20]
    rest=len(items)-len(vis)
    block="\n".join(vis)+ (f"\n외 {rest}개…" if rest>0 else "")
    if not block: block="표시할 항목이 없습니다"
    return set_v2(discord.Embed(
        title="구매 성공",
        description=f"제품 이름 : {product}\n구매 개수 : {qty}\n차감 금액 : {price}\n{line}\n{block}",
        color=GREEN
    ))

# ===== 자동충전(계좌) =====
TOPUP_TIMEOUT_SEC = 5*60
def expire_old_requests():
    now=_now(); changed=False
    for r in DB["topups"]["requests"]:
        if r.get("status","pending")=="pending" and now - int(r.get("ts",now)) > TOPUP_TIMEOUT_SEC:
            r["status"]="expired"; changed=True
    if changed: db_save()

def _hash_receipt(gid:int, amount:int, depositor:str):
    bucket=_now()//10
    base=f"{gid}|{amount}|{str(depositor).lower()}|{bucket}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]

async def handle_deposit(guild: discord.Guild, amount: int, depositor: str):
    expire_old_requests()
    key=_hash_receipt(guild.id, int(amount), str(depositor))
    if any(rc.get("hash")==key for rc in DB["topups"]["receipts"]):
        return False, "duplicate"
    now=_now()
    pending=[r for r in DB["topups"]["requests"]
             if r.get("status","pending")=="pending"
             and r.get("guildId")==guild.id
             and now - int(r.get("ts",now)) <= TOPUP_TIMEOUT_SEC
             and int(r.get("amount",0))==int(amount)]
    exact=[r for r in pending if str(r.get("depositor","")).strip().lower()==str(depositor).strip().lower()]
    exact.sort(key=lambda r:int(r.get("ts",0)), reverse=True)
    pending.sort(key=lambda r:int(r.get("ts",0)), reverse=True)
    target = exact[0] if exact else (pending[0] if pending else None)
    matched_user_id=None
    if target:
        matched_user_id=int(target["userId"])
        target["status"]="ok"
        bal_add(guild.id, matched_user_id, int(amount))
        db_save()
        try:
            user=guild.get_member(matched_user_id) or await guild.fetch_member(matched_user_id)
            dm=await user.create_dm()
            await dm.send(f"[자동충전 완료]\n금액: {amount}원\n입금자: {depositor}")
        except: pass
    DB["topups"]["receipts"].append({
        "hash":key,"guildId":guild.id,"amount":int(amount),
        "depositor":str(depositor),"ts":_now(),"userId":matched_user_id
    }); db_save()
    return (True,"matched") if matched_user_id else (False,"queued")

# ===== 컬쳐 세션 쿠키 저장/복원 =====
CULTURE_K = os.getenv("CULTURE_K", "change_me")
def _enc(plain: str) -> str:
    return base64.b64encode((plain or "").encode()).decode()
def _dec(cipher: str) -> str:
    try: return base64.b64decode(cipher.encode()).decode()
    except: return ""

def _save_culture_cookies(gid:int, uid:int, cookies:list[dict]):
    DB["culture_accounts"].setdefault(str(gid), {}).setdefault(str(uid), {})
    DB["culture_accounts"][str(gid)][str(uid)]["cookies"] = cookies
    DB["culture_accounts"][str(gid)][str(uid)]["cookiesAt"] = _now()
    db_save()

async def _restore_culture_cookies(context, gid:int, uid:int):
    acc = DB["culture_accounts"].get(str(gid), {}).get(str(uid)) or {}
    cookies = acc.get("cookies") or []
    if cookies:
        try:
            await context.add_cookies(cookies)
            return True
        except:
            return False
    return False

def _cookies_expired(gid:int, uid:int, ttl_sec:int=60*60*12):
    acc = DB["culture_accounts"].get(str(gid), {}).get(str(uid)) or {}
    ts = int(acc.get("cookiesAt") or 0)
    return (_now() - ts) > ttl_sec

# ===== 컬쳐랜드 자동화(세션 우선+로그 기록) =====
async def culture_login_and_redeem(pin: str, gid:int, uid:int) -> tuple[bool, int, str]:
    if not PLAYWRIGHT_AVAILABLE:
        return False, 0, "자동화 모듈 미설치(Playwright)."
    acc = DB["culture_accounts"].get(str(gid), {}).get(str(uid))
    if not acc:
        return False, 0, "컬쳐랜드 계정 미등록(/컬쳐랜드_설정)"
    cid=_dec(acc.get("idEnc","")); cpw=_dec(acc.get("pwEnc",""))
    if not cid or not cpw:
        return False, 0, "계정 복호화 실패"
    p = pin.replace("-", "").replace(" ", "")
    if not p.isdigit() or len(p) not in (16, 18, 20):
        return False, 0, "핀 형식 오류"

    from playwright.async_api import async_playwright, TimeoutError as PwTimeout

    LOGIN_URL = "https://m.cultureland.co.kr/mmb/loginMain.do?returnUrl="
    HOME_URL  = "https://m.cultureland.co.kr/main.do"
    CHARGE_18_URL = "https://m.cultureland.co.kr/csh/cshGiftCard.do"
    CHARGE_16_URL = "https://m.cultureland.co.kr/csh/cshGiftCulture.do"

    SEL_ID = "input[type='text'], input[name='userId']"
    SEL_PW = "input[type='password'], input[name='passwd']"
    SEL_LOGIN_BTN = "button:has-text('로그인'), .btnLogin"
    SEL_4 = "input[placeholder='4자리']"
    SEL_6 = "input[placeholder='6자리']"
    SEL_CHARGE_BTN = "button:has-text('충전하기')"

    AMOUNT_REGEX = re.compile(r"([0-9][0-9,]{2,})\s*원")
    ERROR_TEXTS = ["이미 사용", "잘못된", "사용할 수 없는", "충전 불가", "잠시 후 다시", "인증 실패", "한도"]
    OK_TEXTS = ["충전이 완료", "충전되었습니다", "충전 완료"]

    launch_kwargs = dict(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(**launch_kwargs)
        context = await browser.new_context(user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1")
        page = await context.new_page()
        login_fresh = False
        try:
            session_ok=False
            if not _cookies_expired(gid, uid):
                if await _restore_culture_cookies(context, gid, uid):
                    try:
                        await page.goto(HOME_URL, timeout=15000)
                        html = await page.content()
                        if ("로그아웃" in html) or ("마이페이지" in html) or ("내 정보" in html):
                            session_ok=True
                    except:
                        session_ok=False

            if not session_ok:
                await page.goto(LOGIN_URL, timeout=20000)
                id_el = await page.query_selector(SEL_ID) or (await page.query_selector_all("input"))[0]
                await id_el.fill(cid)
                pw_el = await page.query_selector(SEL_PW) or (await page.query_selector_all("input[type='password']"))[0]
                await pw_el.fill(cpw)
                btn = await page.query_selector(SEL_LOGIN_BTN) or await page.query_selector("button")
                await btn.click()
                await page.wait_for_timeout(1500)
                html = await page.content()
                if "hCaptcha" in html or "캡차" in html:
                    return False, 0, "캡차 차단"
                if "비밀번호" in html and "오류" in html:
                    return False, 0, "로그인 실패"
                # 로그인 성공 로그
                await send_log_text(bot.get_guild(gid), "admin", f"[컬쳐랜드] 로그인 성공 uid={uid}")
                try:
                    cookies = await context.cookies()
                    _save_culture_cookies(gid, uid, cookies)
                except:
                    pass
                login_fresh=True

            if len(p)==18:
                await page.goto(CHARGE_18_URL, timeout=20000)
                g1=p[0:4]; g2=p[4:8]; g3=p[8:12]; g4=p[12:16]; g5=p[16:22]
                boxes4 = await page.query_selector_all(SEL_4) or await page.query_selector_all("input[maxlength='4'], input[pattern='[0-9]{4}']")
                if len(boxes4)<4: return False, 0, "18자리 입력칸 부족"
                await boxes4[0].fill(g1); await boxes4[1].fill(g2); await boxes4[2].fill(g3); await boxes4[3].fill(g4)
                box6 = await page.query_selector(SEL_6) or await page.query_selector("input[maxlength='6']")
                if not box6: return False, 0, "18자리 6칸 없음"
                await box6.fill(g5)
            else:
                await page.goto(CHARGE_16_URL, timeout=20000)
                g1=p[0:4]; g2=p[4:8]; g3=p[8:12]; g4=p[12:16]
                boxes4 = await page.query_selector_all(SEL_4) or await page.query_selector_all("input[maxlength='4'], input[pattern='[0-9]{4}']")
                if len(boxes4)<4: return False, 0, "16자리 입력칸 부족"
                await boxes4[0].fill(g1); await boxes4[1].fill(g2); await boxes4[2].fill(g3); await boxes4[3].fill(g4)

            cbtn = await page.query_selector(SEL_CHARGE_BTN) or await page.query_selector("button:has-text('충전')")
            if not cbtn: return False, 0, "충전 버튼 없음"
            await cbtn.click()

            await page.wait_for_timeout(1500)
            html2 = await page.content()
            for fail in ERROR_TEXTS:
                if fail in html2:
                    return False, 0, f"충전 실패: {fail}"

            amount=0
            m = re.search(r"([0-9][0-9,]{2,})\s*원", html2)
            if m:
                try: amount=int(m.group(1).replace(",",""))
                except: amount=0
            ok = any(t in html2 for t in OK_TEXTS)
            if ok and amount>0:
                return True, amount, ""

            await page.wait_for_timeout(900)
            html3 = await page.content()
            for fail in ERROR_TEXTS:
                if fail in html3:
                    return False, 0, f"충전 실패: {fail}"
            m2 = re.search(r"([0-9][0-9,]{2,})\s*원", html3)
            if m2:
                try: amount=int(m2.group(1).replace(",",""))
                except: amount=0
            ok2 = any(t in html3 for t in OK_TEXTS)
            if ok2 and amount>0:
                return True, amount, ""
            return False, 0, "결과 확인 실패"
        except PwTimeout:
            return False, 0, "응답 지연"
        except NotImplementedError:
            return False, 0, "호스트가 하위 프로세스 미지원"
        except Exception as e:
            return False, 0, f"자동화 예외: {str(e)[:120]}"
        finally:
            try:
                cookies = await context.cookies()
                _save_culture_cookies(gid, uid, cookies)
            except:
                pass
            with contextlib.suppress(Exception): await context.close()
            with contextlib.suppress(Exception): await browser.close()

# ===== 후기(1회 제한) =====
def can_send_review(gid:int, uid:int, unique_key:str) -> bool:
    DB["purchases_sent"].setdefault(str(gid), {}).setdefault(str(uid), {})
    return not DB["purchases_sent"][str(gid)][str(uid)].get(unique_key, False)

def lock_review(gid:int, uid:int, unique_key:str):
    DB["purchases_sent"].setdefault(str(gid), {}).setdefault(str(uid), {})
    DB["purchases_sent"][str(gid)][str(uid)][unique_key]=True
    db_save()

class ReviewSendModal(discord.ui.Modal, title="구매 후기 작성"):
    product_input = discord.ui.TextInput(label="구매 제품", required=True, max_length=60)
    stars_input   = discord.ui.TextInput(label="별점(1~5)", required=True, max_length=1)
    content_input = discord.ui.TextInput(label="후기 내용", style=discord.TextStyle.paragraph, required=True, max_length=500)
    def __init__(self, gid:int, uid:int, unique_key:str, default_product:str=""):
        super().__init__()
        self.gid=gid; self.uid=uid; self.unique_key=unique_key
        if default_product: self.product_input.default=default_product
    async def on_submit(self, it: discord.Interaction):
        if not can_send_review(self.gid, self.uid, self.unique_key):
            await it.response.send_message(embed=set_v2(discord.Embed(title="후기 전송 불가", description="이미 작성됨", color=PINK)), ephemeral=True); return
        s=str(self.stars_input.value).strip()
        if not s.isdigit() or not (1<=int(s)<=5):
            await it.response.send_message("별점은 1~5 숫자", ephemeral=True); return
        product=str(self.product_input.value).strip()
        content=str(self.content_input.value).strip()
        e = emb_review_full(product, int(s), content)
        guild = it.guild or bot.get_guild(GUILD_ID)
        if guild: await send_log_embed(guild, "review", e)
        lock_review(self.gid, self.uid, self.unique_key)
        await it.response.send_message("후기 전송 완료", ephemeral=True)

class ReviewButtonView(discord.ui.View):
    def __init__(self, gid:int, uid:int, unique_key:str, default_product:str=""):
        super().__init__(timeout=None)
        btn = discord.ui.Button(label=f"{EMJ_HEART} 후기 전송", style=discord.ButtonStyle.secondary)
        async def _cb(i:discord.Interaction):
            if i.user.id!=uid:
                await i.response.send_message("구매자만 가능", ephemeral=True); return
            if not can_send_review(gid, uid, unique_key):
                await i.response.send_message("이미 작성됨", ephemeral=True); return
            await i.response.send_modal(ReviewSendModal(gid, uid, unique_key, default_product))
        btn.callback=_cb
        self.add_item(btn)

# ===== 충전(계좌 승인/거부) =====
class SecureApproveView(discord.ui.View):
    def __init__(self, payload: dict):
        super().__init__(timeout=TOPUP_TIMEOUT_SEC)
        b_ok=discord.ui.Button(label="승인", style=discord.ButtonStyle.success, emoji=safe_emoji(EMJ_APPROVE))
        b_no=discord.ui.Button(label="거부", style=discord.ButtonStyle.danger,  emoji=safe_emoji(EMJ_DECLINE))
        async def _ok(i:discord.Interaction):
            await notify_user_topup_result(i.client, payload, True)
            await i.response.edit_message(embed=set_v2(discord.Embed(title="승인 완료", description="해당 충전신청을 승인했습니다.", color=GREEN)), view=None)
        async def _no(i:discord.Interaction):
            await notify_user_topup_result(i.client, payload, False)
            await i.response.edit_message(embed=set_v2(discord.Embed(title="거부 완료", description="해당 충전신청을 거부했습니다.", color=RED)), view=None)
        b_ok.callback=_ok; b_no.callback=_no
        self.add_item(b_ok); self.add_item(b_no)

async def notify_user_topup_result(client: discord.Client, payload: dict, approved: bool):
    gid=int(payload["guild_id"]); uid=int(payload["user_id"])
    guild = client.get_guild(gid)
    if not guild: return
    try:
        user = guild.get_member(uid) or await guild.fetch_member(uid)
        e=set_v2(discord.Embed(
            title=("충전완료" if approved else "충전실패"),
            description=("충전신청이 성공적으로 완료되었습니다" if approved else "충전신청이 거부되었습니다"),
            color=(GREEN if approved else RED)
        ))
        dm=await user.create_dm()
        await dm.send(embed=e)
    except: pass

class PaymentModal(discord.ui.Modal, title="충전 신청"):
    amount_input = discord.ui.TextInput(label="충전할 금액", required=True, max_length=12)
    depositor_input = discord.ui.TextInput(label="입금자명", required=True, max_length=20)
    def __init__(self, owner_id:int):
        super().__init__(); self.owner_id=owner_id
    async def on_submit(self, it: discord.Interaction):
        try:
            amt_raw=str(self.amount_input.value).strip().replace(",","")
            amt=int(amt_raw) if amt_raw.isdigit() else 0
            depos=str(self.depositor_input.value).strip()
            if amt>0 and depos:
                DB["topups"]["requests"].append({
                    "guildId": it.guild.id, "userId": it.user.id,
                    "amount": amt, "depositor": depos, "ts": _now(), "status": "pending"
                }); db_save()
        except: pass
        bank=DB["account"].get("bank","미등록")
        holder=DB["account"].get("holder","미등록")
        number=DB["account"].get("number","미등록")
        amount_txt=f"{amt_raw}원" if amt_raw else "0원"
        e_user=set_v2(discord.Embed(
            title="충전신청",
            description=f"은행명 : {bank}\n예금주 : {holder}\n계좌번호 : `{number}`\n보내야할 금액 : {amount_txt}",
            color=GREEN
        ))
        await it.response.send_message(embed=e_user, ephemeral=True)
        secure_ch=get_log_channel(it.guild, "secure")
        if secure_ch:
            payload={"guild_id":it.guild.id,"user_id":it.user.id,"amount":amt,"amount_txt":amount_txt,"depositor":depos}
            e_sec=set_v2(discord.Embed(
                title="충전알림",
                description=f"유저 : {it.user.mention}\n충전 금액 : {amount_txt}\n입금자명 : {depos}",
                color=ORANGE
            ))
            await secure_ch.send(embed=e_sec, view=SecureApproveView(payload))

# ===== 컬쳐 설정/모달 =====
class CultureAccountModal(discord.ui.Modal, title="컬쳐랜드 설정"):
    id_input = discord.ui.TextInput(label="ID", required=True, max_length=60)
    pw_input = discord.ui.TextInput(label="PW", required=True, max_length=80)
    opt_input= discord.ui.TextInput(label="옵션(선택)", required=False, max_length=50)
    def __init__(self, owner_id:int):
        super().__init__(); self.owner_id=owner_id
    async def on_submit(self, it: discord.Interaction):
        if it.user.id != self.owner_id:
            await it.response.send_message("작성자만 설정 가능", ephemeral=True); return
        gid=str(it.guild.id); uid=str(it.user.id)
        DB["culture_accounts"].setdefault(gid, {})
        DB["culture_accounts"][gid][uid] = {
            "idEnc": _enc(str(self.id_input.value).strip()),
            "pwEnc": _enc(str(self.pw_input.value).strip()),
            "options": str(self.opt_input.value).strip(),
            "cookies": DB["culture_accounts"].get(gid, {}).get(uid, {}).get("cookies", []),
            "cookiesAt": DB["culture_accounts"].get(gid, {}).get(uid, {}).get("cookiesAt", 0),
            "createdAt": _now(),
            "updatedAt": _now()
        }
        db_save()
        await it.response.send_message(embed=set_v2(discord.Embed(title="컬쳐랜드 계정 저장 완료", description="문상결제에서 자동 사용됩니다.", color=GRAY)), ephemeral=True)

class CulturePinModal(discord.ui.Modal, title="문화상품권 충전(컬쳐랜드)"):
    pin_input = discord.ui.TextInput(label="핀코드(하이픈 없이)", required=True, max_length=32)
    def __init__(self, owner_id:int):
        super().__init__(); self.owner_id=owner_id
    async def on_submit(self, it: discord.Interaction):
        pin = str(self.pin_input.value).strip()
        ok, amount, reason = await culture_login_and_redeem(pin, it.guild.id, it.user.id)
        if not ok or amount <= 0:
            await it.response.send_message(embed=set_v2(discord.Embed(title="충전실패", description=reason or "검증 실패", color=RED)), ephemeral=True); return
        res_ok, _ = await handle_deposit(it.guild, int(amount), "문화상품권(컬쳐랜드)")
        if res_ok:
            await it.response.send_message(embed=set_v2(discord.Embed(title="충전완료", description=f"{amount}원 충전되었습니다", color=GREEN)), ephemeral=True)
        else:
            await it.response.send_message(embed=set_v2(discord.Embed(title="충전대기", description="잠시 후 반영됩니다.", color=ORANGE)), ephemeral=True)

# ===== 결제수단 뷰 =====
class PaymentMethodView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        btns=[]
        if DB["payments"].get("bank", False):
            btns.append(discord.ui.Button(label="계좌이체", style=discord.ButtonStyle.secondary, emoji=safe_emoji(EMJ_TOSS)))
        if DB["payments"].get("culture", False):
            btns.append(discord.ui.Button(label="문상결제", style=discord.ButtonStyle.secondary, emoji=safe_emoji(EMJ_CULTURE)))
        if DB["payments"].get("coin", False):
            btns.append(discord.ui.Button(label="코인결제", style=discord.ButtonStyle.secondary, emoji=safe_emoji(EMJ_COIN)))
        for b in btns:
            async def _cb(i:discord.Interaction, label=b.label):
                if label=="계좌이체":
                    await i.response.send_modal(PaymentModal(i.user.id))
                elif label=="문상결제":
                    if not PLAYWRIGHT_AVAILABLE:
                        await i.response.send_message("자동화 모듈 미설치(Playwright).", ephemeral=True); return
                    await i.response.send_modal(CulturePinModal(i.user.id))
                else:
                    await i.response.send_message(embed=set_v2(discord.Embed(title="실패", description="현재 미지원", color=RED)), ephemeral=True)
            b.callback=_cb
            self.add_item(b)

# ===== 카테고리/제품(예전 플로우) =====
def build_category_embed():
    lines=[]
    if DB["categories"]:
        for c in DB["categories"]:
            prod_count = len([p for p in DB["products"] if p["category"]==c["name"]])
            stars=category_avg_stars(c["name"])
            lines.append(f"**카테고리명 : {c['name']}**")
            lines.append(f"-# 제품 : {prod_count}")
            lines.append(f"-# 별점 : {stars}")
            lines.append("ㅡ"*18)
    else:
        lines.append("등록된 카테고리가 없습니다")
    return set_v2(discord.Embed(title="카테고리를 선택해주세요", description="\n".join(lines), color=GRAY))

class QuantityModal(discord.ui.Modal, title="수량 입력"):
    qty_input = discord.ui.TextInput(label="구매 수량", required=True, max_length=6)
    def __init__(self, owner_id:int, category:str, product_name:str):
        super().__init__(); self.owner_id=owner_id; self.category=category; self.product_name=product_name
    async def on_submit(self, it: discord.Interaction):
        if it.user.id!=self.owner_id:
            await it.response.send_message("작성자만 사용 가능", ephemeral=True); return
        s=str(self.qty_input.value).strip()
        if not s.isdigit() or int(s)<=0:
            await it.response.send_message("수량은 1 이상의 숫자", ephemeral=True); return
        qty=int(s); p=prod_get(self.product_name, self.category)
        if not p:
            await it.response.send_message("유효하지 않은 제품", ephemeral=True); return
        if p["stock"]<qty:
            await it.response.send_message(embed=set_v2(discord.Embed(title="재고 부족", description=f"{self.product_name} 재고가 부족합니다.", color=ORANGE)), ephemeral=True); return
        taken=[]; cnt=qty
        while cnt>0 and p["items"]:
            taken.append(p["items"].pop(0)); cnt-=1
        p["stock"]-=qty; p["sold_count"]+=qty; db_save()
        bal_sub(it.guild.id, it.user.id, p["price"]*qty)
        try:
            dm=await it.user.create_dm()
            unique_key=f"{it.guild.id}:{it.user.id}:{self.product_name}:{_now()}"
            await dm.send(embed=emb_purchase_dm(self.product_name, qty, p["price"], taken), view=ReviewButtonView(it.guild.id, it.user.id, unique_key, self.product_name))
        except: pass
        try:
            await send_log_embed(it.guild, "purchase", emb_purchase_log(it.user, self.product_name, qty))
        except: pass
        await it.response.send_message(embed=set_v2(discord.Embed(title="구매 완료", description=f"{self.product_name} 구매가 완료되었습니다. DM을 확인해주세요.", color=GREEN)), ephemeral=True)

class ProductSelect(discord.ui.Select):
    def __init__(self, owner_id:int, category:str):
        prods=prod_list_by_cat(category)
        opts=[]
        if prods:
            for p in prods[:25]:
                opts.append(discord.SelectOption(label=p["name"], value=p["name"], description=f"가격 {p['price']}"))
        else:
            opts=[discord.SelectOption(label="해당 카테고리에 제품이 없습니다", value="__none__")]
        super().__init__(placeholder="제품을 선택하세요", min_values=1, max_values=1, options=opts, custom_id=f"prod_sel_{owner_id}")
        self.owner_id=owner_id; self.category=category
    async def callback(self, it: discord.Interaction):
        if it.user.id!=self.owner_id:
            await it.response.send_message("작성자만 사용 가능", ephemeral=True); return
        val=self.values[0]
        if val=="__none__":
            await it.response.send_message("먼저 제품을 추가해주세요.", ephemeral=True); return
        await it.response.send_modal(QuantityModal(self.owner_id, self.category, val))

class CategorySelectForBuy(discord.ui.Select):
    def __init__(self, owner_id:int):
        cats=DB["categories"]
        if cats:
            opts=[discord.SelectOption(label=c["name"], value=c["name"], description=(c.get("desc")[:80] if c.get("desc") else None)) for c in cats[:25]]
        else:
            opts=[discord.SelectOption(label="등록된 카테고리가 없습니다", value="__none__")]
        super().__init__(placeholder="카테고리를 선택하세요", min_values=1, max_values=1, options=opts, custom_id=f"cat_buy_{owner_id}")
        self.owner_id=owner_id
    async def callback(self, it: discord.Interaction):
        if it.user.id!=self.owner_id:
            await it.response.send_message("작성자만 사용 가능", ephemeral=True); return
        val=self.values[0]
        if val=="__none__":
            await it.response.send_message("먼저 카테고리를 추가해주세요.", ephemeral=True); return
        e=set_v2(discord.Embed(title="제품 선택하기", description="제품을 선택해주세요", color=GRAY))
        v=discord.ui.View(timeout=None); v.add_item(ProductSelect(self.owner_id, val))
        await it.response.send_message(embed=e, view=v, ephemeral=True)

class CategorySelectForBuyView(discord.ui.View):
    def __init__(self, owner_id:int):
        super().__init__(timeout=None); self.add_item(CategorySelectForBuy(owner_id))

# ===== 버튼 패널 =====
class ButtonPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        n=discord.ui.Button(label="공지사항", style=discord.ButtonStyle.secondary, emoji=safe_emoji(EMJ_NOTICE), row=0)
        c=discord.ui.Button(label="충전",   style=discord.ButtonStyle.secondary, emoji=safe_emoji(EMJ_CHARGE), row=0)
        i=discord.ui.Button(label="내 정보", style=discord.ButtonStyle.secondary, emoji=safe_emoji(EMJ_INFO),   row=1)
        b=discord.ui.Button(label="구매",   style=discord.ButtonStyle.secondary, emoji=safe_emoji(EMJ_BUY),    row=1)
        async def _notice(it):
            await it.response.send_message(embed=set_v2(discord.Embed(title="공지사항", description="서버규칙 필독 부탁드립니다\n자충 오류시 티켓 열어주세요", color=GRAY)), ephemeral=True)
        async def _charge(it):
            if ban_is_blocked(it.guild.id, it.user.id):
                await it.response.send_message(embed=set_v2(discord.Embed(title="이용 불가", description="차단 상태입니다. /유저_설정으로 해제하세요.", color=RED)), ephemeral=True); return
            view=PaymentMethodView()
            if len(view.children)==0:
                await it.response.send_message(embed=set_v2(discord.Embed(title="결제수단 선택하기", description="현재 지원되는 결제수단이 없습니다.", color=ORANGE)), ephemeral=True)
            else:
                await it.response.send_message(embed=set_v2(discord.Embed(title="결제수단 선택하기", description="원하시는 결제수단 버튼을 클릭해주세요", color=GRAY)), view=view, ephemeral=True)
        async def _info(it):
            gid=it.guild.id; uid=it.user.id
            ords=orders_get(gid, uid); spent=0
            for o in ords:
                p=next((pp for pp in DB["products"] if pp["name"]==o["product"]), None)
                if p: spent += p["price"]*o["qty"]
            bal=bal_get(gid, uid); pts=pt_get(gid, uid)
            line="ㅡ"*18
            desc=f"보유 금액 : {bal}\n누적 금액 : {spent}\n포인트 : {pts}\n거래 횟수 : {len(ords)}\n{line}\n역할등급 : 아직 없습니다\n역할혜택 : 아직 없습니다"
            e=set_v2(discord.Embed(title="내 정보", description=desc, color=GRAY))
            try: e.set_thumbnail(url=it.user.display_avatar.url)
            except: pass
            await it.response.send_message(embed=e, view=MyInfoView(uid, ords), ephemeral=True)
        async def _buy(it):
            if ban_is_blocked(it.guild.id, it.user.id):
                await it.response.send_message(embed=set_v2(discord.Embed(title="이용 불가", description="차단 상태입니다. /유저_설정으로 해제하세요.", color=RED)), ephemeral=True); return
            e = build_category_embed()
            v = CategorySelectForBuyView(it.user.id)
            await it.response.send_message(embed=e, view=v, ephemeral=True)
        n.callback=_notice; c.callback=_charge; i.callback=_info; b.callback=_buy
        self.add_item(n); self.add_item(c); self.add_item(i); self.add_item(b)

# ===== 내 정보 =====
class RecentOrdersSelect(discord.ui.Select):
    def __init__(self, owner_id:int, orders:list[dict]):
        opts=[]
        for o in orders[-5:][::-1]:
            ts=time.strftime('%Y-%m-%d %H:%M', time.localtime(o['ts']))
            opts.append(discord.SelectOption(label=f"{o['product']} x{o['qty']}", description=ts, value=f"{o['product']}||{o['qty']}||{o['ts']}"))
        if not opts:
            opts=[discord.SelectOption(label="최근 구매 없음", value="__none__", description="표시할 항목이 없습니다")]
        super().__init__(placeholder="최근 구매 내역 보기", min_values=1, max_values=1, options=opts, custom_id=f"recent_{owner_id}")
        self.owner_id=owner_id
    async def callback(self, it: discord.Interaction):
        if it.user.id!=self.owner_id:
            await it.response.send_message("작성자만 볼 수 있어.", ephemeral=True); return
        val=self.values[0]
        if val=="__none__":
            await it.response.send_message("최근 구매가 없습니다.", ephemeral=True); return
        name, qty, ts = val.split("||")
        ts_str=time.strftime('%Y-%m-%d %H:%M', time.localtime(int(ts)))
        await it.response.send_message(embed=set_v2(discord.Embed(title="구매 상세", description=f"- 제품: {name}\n- 수량: {qty}\n- 시간: {ts_str}", color=GRAY)), ephemeral=True)

class MyInfoView(discord.ui.View):
    def __init__(self, owner_id:int, orders:list[dict]):
        super().__init__(timeout=None); self.add_item(RecentOrdersSelect(owner_id, orders))

# ===== 관리자 보호 =====
def is_admin():
    async def predicate(interaction: discord.Interaction):
        if interaction.user.guild_permissions.manage_guild:
            return True
        await interaction.response.send_message("관리자만 사용할 수 있어.", ephemeral=True)
        return False
    return app_commands.check(predicate)

# ===== 슬래시 명령어(11개) =====
class CategoryDeleteView(discord.ui.View):
    def __init__(self, owner_id:int):
        super().__init__(timeout=None)
        class CategoryDeleteSelect(discord.ui.Select):
            def __init__(self, owner_id:int):
                cats=DB["categories"]; opts=[]
                for c in cats[:25]:
                    opts.append(discord.SelectOption(label=c["name"], value=c["name"], description=(c.get("desc")[:80] if c.get("desc") else None)))
                super().__init__(placeholder="삭제할 카테고리를 선택하세요", min_values=1, max_values=1, options=opts or [discord.SelectOption(label="삭제할 카테고리가 없습니다", value="__none__")], custom_id=f"cat_del_{owner_id}")
                self.owner_id=owner_id
            async def callback(self, it: discord.Interaction):
                if it.user.id!=self.owner_id:
                    await it.response.send_message("작성자만 선택 가능", ephemeral=True); return
                val=self.values[0]
                if val=="__none__":
                    await it.response.send_message("삭제할 카테고리가 없습니다.", ephemeral=True); return
                DB["categories"]=[c for c in DB["categories"] if c["name"]!=val]
                DB["products"]=[p for p in DB["products"] if p["category"]!=val]; db_save()
                await it.response.send_message(embed=set_v2(discord.Embed(title="카테고리 삭제 완료", description=f"삭제된 카테고리: {val}", color=GRAY)), ephemeral=True)
        self.add_item(CategoryDeleteSelect(owner_id))

class CategorySetupModal(discord.ui.Modal, title="카테고리 추가"):
    name_input = discord.ui.TextInput(label="카테고리 이름", required=True, max_length=60)
    desc_input = discord.ui.TextInput(label="카테고리 설명", style=discord.TextStyle.paragraph, required=False, max_length=200)
    emoji_input= discord.ui.TextInput(label="카테고리 이모지", required=False, max_length=100)
    def __init__(self, owner_id:int):
        super().__init__(); self.owner_id=owner_id
    async def on_submit(self, it: discord.Interaction):
        if it.user.id!=self.owner_id:
            await it.response.send_message("작성자만 사용 가능", ephemeral=True); return
        name=str(self.name_input.value).strip()
        desc=str(self.desc_input.value).strip() if self.desc_input.value else ""
        emoji=str(self.emoji_input.value).strip() if self.emoji_input.value else ""
        i=next((k for k,c in enumerate(DB["categories"]) if c["name"]==name), -1)
        row={"name":name,"desc":desc,"emoji_raw":emoji}
        if i>=0: DB["categories"][i]=row
        else: DB["categories"].append(row)
        db_save()
        await it.response.send_message(embed=set_v2(discord.Embed(title="카테고리 등록 완료", description=f"{name}\n{desc}", color=GRAY)), ephemeral=True)

class StockAddModal(discord.ui.Modal, title="재고 추가"):
    lines_input = discord.ui.TextInput(label="재고 추가(줄마다 1개)", style=discord.TextStyle.paragraph, required=True, max_length=4000)
    def __init__(self, owner_id:int, name:str, category:str):
        super().__init__(); self.owner_id=owner_id; self.name=name; self.category=category
    async def on_submit(self, it: discord.Interaction):
        if it.user.id!=self.owner_id:
            await it.response.send_message("작성자만 사용 가능", ephemeral=True); return
        lines=[ln.strip() for ln in str(self.lines_input.value).splitlines() if ln.strip()]
        p=prod_get(self.name, self.category)
        if not p:
            await it.response.send_message("유효하지 않은 제품입니다.", ephemeral=True); return
        p["items"].extend(lines); p["stock"]+=len(lines); db_save()
        await it.response.send_message(embed=set_v2(discord.Embed(title="재고 추가 완료", description=f"{self.name} +{len(lines)} → 재고 {p['stock']}", color=GRAY)), ephemeral=True)

class ProductSetupModal(discord.ui.Modal, title="제품 추가"):
    name_input = discord.ui.TextInput(label="제품 이름", required=True, max_length=60)
    category_input = discord.ui.TextInput(label="카테고리 이름", required=True, max_length=60)
    price_input = discord.ui.TextInput(label="제품 가격(원)", required=True, max_length=10)
    emoji_input = discord.ui.TextInput(label="제품 이모지", required=False, max_length=100)
    desc_input  = discord.ui.TextInput(label="제품 설명", style=discord.TextStyle.paragraph, required=False, max_length=400)
    def __init__(self, owner_id:int):
        super().__init__(); self.owner_id=owner_id
    async def on_submit(self, it: discord.Interaction):
        if it.user.id!=self.owner_id:
            await it.response.send_message("작성자만 사용 가능", ephemeral=True); return
        name=str(self.name_input.value).strip()
        cat=str(self.category_input.value).strip()
        price_s=str(self.price_input.value).strip()
        if not any(c["name"]==cat for c in DB["categories"]):
            await it.response.send_message("해당 카테고리가 없습니다.", ephemeral=True); return
        if not price_s.isdigit():
            await it.response.send_message("가격은 숫자만 입력", ephemeral=True); return
        price=int(price_s)
        emoji=str(self.emoji_input.value).strip() if self.emoji_input.value else ""
        desc=str(self.desc_input.value).strip() if self.desc_input.value else ""
        prod_upsert(name, cat, price, emoji, desc)
        await it.response.send_message(embed=set_v2(discord.Embed(title="제품 등록 완료", description=f"{name}\n카테고리: {cat}\n가격: {price}\n(설명 저장됨)", color=GRAY)), ephemeral=True)

class ProductDeleteView(discord.ui.View):
    def __init__(self, owner_id:int):
        super().__init__(timeout=None)
        class ProductDeleteSelect(discord.ui.Select):
            def __init__(self, owner_id:int):
                ps=prod_list_all(); opts=[]
                for p in ps[:25]:
                    opts.append(discord.SelectOption(label=p["name"], value=f"{p['name']}||{p['category']}", description=f"{p['category']}"))
                super().__init__(placeholder="삭제할 제품을 선택", min_values=1, max_values=1, options=opts or [discord.SelectOption(label="삭제할 제품이 없습니다", value="__none__")], custom_id=f"prod_del_{owner_id}")
                self.owner_id=owner_id
            async def callback(self, it: discord.Interaction):
                if it.user.id!=self.owner_id:
                    await it.response.send_message("작성자만 사용 가능", ephemeral=True); return
                val=self.values[0]
                if val=="__none__":
                    await it.response.send_message("삭제할 제품이 없습니다.", ephemeral=True); return
                name,cat=val.split("||",1)
                prod_delete(name, cat)
                await it.response.send_message(embed=set_v2(discord.Embed(title="제품 삭제 완료", description=f"삭제된 제품: {name} (카테고리: {cat})", color=GRAY)), ephemeral=True)
        self.add_item(ProductDeleteSelect(owner_id))

class ControlCog(commands.Cog):
    def __init__(self, bot_:commands.Bot):
        self.bot=bot_

    @app_commands.command(name="버튼패널", description="버튼 패널")
    @app_commands.guilds(GUILD)
    async def 버튼패널(self, it: discord.Interaction):
        await it.response.send_message(embed=set_v2(discord.Embed(title="윈드 OTT", description="아래 버튼으로 이용해주세요!", color=GRAY)), view=ButtonPanel())

    @app_commands.command(name="카테고리_설정", description="카테고리 설정")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 카테고리_설정(self, it:discord.Interaction):
        view=discord.ui.View(timeout=None)
        class Root(discord.ui.Select):
            def __init__(self, owner_id:int):
                super().__init__(placeholder="카테고리 설정하기", min_values=1, max_values=1,
                                 options=[discord.SelectOption(label="카테고리 추가", value="add"),
                                          discord.SelectOption(label="카테고리 삭제", value="del")],
                                 custom_id=f"cat_root_{owner_id}")
                self.owner_id=owner_id
            async def callback(self, inter:discord.Interaction):
                if inter.user.id!=self.owner_id:
                    await inter.response.send_message("작성자만 사용 가능", ephemeral=True); return
                if self.values[0]=="add":
                    await inter.response.send_modal(CategorySetupModal(self.owner_id))
                else:
                    await inter.response.send_message(embed=set_v2(discord.Embed(title="카테고리 삭제", description="삭제할 카테고리를 선택하세요.", color=GRAY)), view=CategoryDeleteView(self.owner_id), ephemeral=True)
        view.add_item(Root(it.user.id))
        await it.response.send_message(embed=set_v2(discord.Embed(title="카테고리 설정하기", description="카테고리 설정해주세요", color=GRAY)), view=view, ephemeral=True)

    @app_commands.command(name="제품_설정", description="제품 설정")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 제품_설정(self, it:discord.Interaction):
        view=discord.ui.View(timeout=None)
        class Root(discord.ui.Select):
            def __init__(self, owner_id:int):
                super().__init__(placeholder="제품 설정하기", min_values=1, max_values=1,
                                 options=[discord.SelectOption(label="제품 추가", value="add"),
                                          discord.SelectOption(label="제품 삭제", value="del")],
                                 custom_id=f"prod_root_{owner_id}")
                self.owner_id=owner_id
            async def callback(self, inter:discord.Interaction):
                if inter.user.id!=self.owner_id:
                    await inter.response.send_message("작성자만 사용 가능", ephemeral=True); return
                if self.values[0]=="add":
                    await inter.response.send_modal(ProductSetupModal(self.owner_id))
                else:
                    await inter.response.send_message(embed=set_v2(discord.Embed(title="제품 삭제", description="삭제할 제품을 선택하세요.", color=GRAY)), view=ProductDeleteView(self.owner_id), ephemeral=True)
        view.add_item(Root(it.user.id))
        await it.response.send_message(embed=set_v2(discord.Embed(title="제품 설정하기", description="제품 설정해주세요", color=GRAY)), view=view, ephemeral=True)

    @app_commands.command(name="재고_설정", description="재고 설정")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 재고_설정(self, it:discord.Interaction):
        class StockSel(discord.ui.Select):
            def __init__(self, owner_id:int):
                ps=prod_list_all()
                opts=[]
                if ps:
                    for p in ps[:25]:
                        opts.append(discord.SelectOption(label=f"{p['name']} ({p['category']})", value=f"{p['name']}||{p['category']}", description=f"가격 {p['price']}"))
                else:
                    opts=[discord.SelectOption(label="등록된 제품이 없습니다", value="__none__")]
                super().__init__(placeholder="재고를 설정할 제품을 선택", min_values=1, max_values=1, options=opts, custom_id=f"stock_prod_{owner_id}")
                self.owner_id=owner_id
            async def callback(self, inter:discord.Interaction):
                if inter.user.id!=self.owner_id:
                    await inter.response.send_message("작성자만 사용 가능", ephemeral=True); return
                val=self.values[0]
                if val=="__none__":
                    await inter.response.send_message("먼저 제품을 추가해주세요.", ephemeral=True); return
                name,cat=val.split("||",1)
                await inter.response.send_modal(StockAddModal(self.owner_id, name, cat))
        view=discord.ui.View(timeout=None); view.add_item(StockSel(it.user.id))
        await it.response.send_message(embed=set_v2(discord.Embed(title="재고 설정하기", description="재고 설정해주세요", color=GRAY)), view=view, ephemeral=True)

    @app_commands.command(name="로그_설정", description="로그/보안 채널 설정")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 로그_설정(self, it:discord.Interaction):
        class LogChannelIdModal(discord.ui.Modal, title="로그 채널 설정"):
            channel_id_input = discord.ui.TextInput(label="채널 ID", required=True, max_length=25)
            def __init__(self, owner_id:int, log_key:str):
                super().__init__(); self.owner_id=owner_id; self.log_key=log_key
            async def on_submit(self, inter:discord.Interaction):
                if inter.user.id!=self.owner_id:
                    await inter.response.send_message("작성자만 사용 가능", ephemeral=True); return
                raw=str(self.channel_id_input.value).strip()
                if not raw.isdigit():
                    await inter.response.send_message(embed=set_v2(discord.Embed(title="실패", description="채널 ID는 숫자", color=RED)), ephemeral=True); return
                ch=inter.guild.get_channel(int(raw))
                if not isinstance(ch, discord.TextChannel):
                    await inter.response.send_message(embed=set_v2(discord.Embed(title="실패", description="유효한 텍스트 채널 아님", color=RED)), ephemeral=True); return
                DB["logs"].setdefault(self.log_key, {"enabled": False, "target_channel_id": None})
                DB["logs"][self.log_key]["target_channel_id"]=int(raw)
                DB["logs"][self.log_key]["enabled"]=True; db_save()
                pretty={"purchase":"구매로그","review":"구매후기","admin":"관리자로그","secure":"보안채널"}[self.log_key]
                await inter.response.send_message(embed=set_v2(discord.Embed(title=f"{pretty} 채널 지정 완료", description=f"목적지: {ch.mention}", color=GRAY)), ephemeral=True)
        class Root(discord.ui.Select):
            def __init__(self, owner_id:int):
                options=[discord.SelectOption(label="구매로그 설정", value="purchase"),
                         discord.SelectOption(label="구매후기 설정", value="review"),
                         discord.SelectOption(label="관리자로그 설정", value="admin"),
                         discord.SelectOption(label="보안채널 설정(충전승인)", value="secure")]
                super().__init__(placeholder="설정할 로그 유형 선택", min_values=1, max_values=1, options=options, custom_id=f"log_root_{owner_id}")
                self.owner_id=owner_id
            async def callback(self, inter:discord.Interaction):
                if inter.user.id!=self.owner_id:
                    await inter.response.send_message("작성자만 사용 가능", ephemeral=True); return
                await inter.response.send_modal(LogChannelIdModal(self.owner_id, self.values[0]))
        view=discord.ui.View(timeout=None); view.add_item(Root(it.user.id))
        await it.response.send_message(embed=set_v2(discord.Embed(title="로그 설정하기", description="로그/보안 채널을 설정해주세요", color=GRAY)), view=view, ephemeral=True)

    @app_commands.command(name="잔액_설정", description="잔액 추가/차감")
    @app_commands.guilds(GUILD)
    @is_admin()
    @app_commands.describe(유저="대상 유저", 금액="정수 금액", 여부="추가/차감")
    @app_commands.choices(여부=[app_commands.Choice(name="추가", value="추가"),
                               app_commands.Choice(name="차감", value="차감")])
    async def 잔액_설정(self, it:discord.Interaction, 유저:discord.Member, 금액:int, 여부:app_commands.Choice[str]):
        if 금액<0:
            await it.response.send_message("금액은 음수 불가", ephemeral=True); return
        gid=it.guild.id; uid=유저.id; prev=bal_get(gid, uid)
        if 여부.value=="차감":
            bal_sub(gid, uid, 금액); after=bal_get(gid, uid); color=RED; title=f"{유저} 금액 차감"
        else:
            bal_add(gid, uid, 금액); after=bal_get(gid, uid); color=GREEN; title=f"{유저} 금액 추가"
        await it.response.send_message(embed=set_v2(discord.Embed(title=title, description=f"원래 금액 : {prev}\n변경 금액 : {금액}\n변경 후 금액 : {after}", color=color)), ephemeral=True)

    @app_commands.command(name="결제수단_설정", description="결제수단 지원 여부")
    @app_commands.guilds(GUILD)
    @is_admin()
    @app_commands.describe(계좌이체="지원/미지원", 코인결제="지원/미지원", 문상결제="지원/미지원")
    @app_commands.choices(
        계좌이체=[app_commands.Choice(name="지원", value="지원"), app_commands.Choice(name="미지원", value="미지원")],
        코인결제=[app_commands.Choice(name="지원", value="지원"), app_commands.Choice(name="미지원", value="미지원")],
        문상결제=[app_commands.Choice(name="지원", value="지원"), app_commands.Choice(name="미지원", value="미지원")]
    )
    async def 결제수단_설정(self, it:discord.Interaction,
                        계좌이체:app_commands.Choice[str],
                        코인결제:app_commands.Choice[str],
                        문상결제:app_commands.Choice[str]):
        DB["payments"]["bank"]   = (계좌이체.value == "지원")
        DB["payments"]["coin"]   = (코인결제.value == "지원")
        DB["payments"]["culture"]= (문상결제.value == "지원")
        db_save()
        await it.response.send_message(embed=set_v2(discord.Embed(title="결제수단 설정 완료", description=f"계좌이체: {계좌이체.value}\n코인결제: {코인결제.value}\n문상결제: {문상결제.value}", color=GRAY)), ephemeral=True)

    @app_commands.command(name="계좌번호_설정", description="계좌정보 설정")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 계좌번호_설정(self, it:discord.Interaction):
        class AccountSetupModal(discord.ui.Modal, title="계좌번호 설정"):
            bank_input   = discord.ui.TextInput(label="은행명", required=True, max_length=30)
            number_input = discord.ui.TextInput(label="계좌번호", required=True, max_length=40)
            holder_input = discord.ui.TextInput(label="예금주", required=True, max_length=30)
            def __init__(self, owner_id:int):
                super().__init__(); self.owner_id=owner_id
            async def on_submit(self, inter:discord.Interaction):
                if inter.user.id!=self.owner_id:
                    await inter.response.send_message("작성자만 가능", ephemeral=True); return
                DB["account"]["bank"]=str(self.bank_input.value).strip()
                DB["account"]["number"]=str(self.number_input.value).strip()
                DB["account"]["holder"]=str(self.holder_input.value).strip()
                db_save()
                await inter.response.send_message(embed=set_v2(discord.Embed(title="계좌정보 저장 완료", description=f"은행명 `{DB['account']['bank']}`\n계좌번호 `{DB['account']['number']}`\n예금주 `{DB['account']['holder']}`", color=GRAY)), ephemeral=True)
        await it.response.send_modal(AccountSetupModal(it.user.id))

    @app_commands.command(name="유저_설정", description="유저 차단/해제")
    @app_commands.guilds(GUILD)
    @is_admin()
    @app_commands.describe(유저="대상 유저", 여부="차단하기/차단풀기")
    @app_commands.choices(여부=[app_commands.Choice(name="차단하기", value="ban"),
                               app_commands.Choice(name="차단풀기", value="unban")])
    async def 유저_설정(self, it:discord.Interaction, 유저:discord.Member, 여부:app_commands.Choice[str]):
        gid=str(it.guild.id); uid=str(유저.id)
        DB["bans"].setdefault(gid, {})
        if 여부.value=="ban":
            DB["bans"][gid][uid]=True; db_save()
            await it.channel.send(embed=set_v2(discord.Embed(title="차단하기", description=f"{유저}님은 자판기 이용 불가능", color=RED)))
            await it.response.send_message("처리 완료", ephemeral=True)
        else:
            DB["bans"][gid].pop(uid, None); db_save()
            await it.channel.send(embed=set_v2(discord.Embed(title="차단풀기", description=f"{유저}님은 다시 이용 가능", color=GREEN)))
            await it.response.send_message("처리 완료", ephemeral=True)

    @app_commands.command(name="유저_조회", description="유저 조회")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 유저_조회(self, it:discord.Interaction, 유저:discord.Member):
        gid=it.guild.id; uid=유저.id
        ords=orders_get(gid, uid); spent=0
        for o in ords:
            p=next((pp for pp in DB["products"] if pp["name"]==o["product"]), None)
            if p: spent += p["price"]*o["qty"]
        bal=bal_get(gid, uid); pts=pt_get(gid, uid)
        await it.response.send_message(embed=set_v2(discord.Embed(title=f"{유저} 정보", description=f"보유 금액 : `{bal}`\n누적 금액 : `{spent}`\n포인트 : `{pts}`\n거래 횟수 : `{len(ords)}`", color=GRAY)), ephemeral=True)

    @app_commands.command(name="컬쳐랜드_설정", description="컬쳐랜드 계정 등록/갱신")
    @app_commands.guilds(GUILD)
    @is_admin()
    async def 컬쳐랜드_설정(self, it:discord.Interaction):
        await it.response.send_modal(CultureAccountModal(it.user.id))

# ===== FastAPI 웹훅 =====
app = FastAPI()

def parse_sms_kakaobank(msg: str) -> tuple[int | None, str | None]:
    RE_AMOUNT = [re.compile(r"입금\s*([0-9][0-9,]*)\s*원")]
    text = str(msg or ""); amount=None
    for r in RE_AMOUNT:
        m=r.search(text)
        if m:
            raw=m.group(1).replace(",","")
            if raw.isdigit(): amount=int(raw); break
    depositor=None
    lines=[ln.strip() for ln in text.splitlines() if ln.strip()]
    for i,l in enumerate(lines):
        if l.startswith("입금"):
            if i+1<len(lines): depositor = lines[i+1].split()[0]
            break
    if depositor and ("잔액" in depositor or depositor.startswith("잔액")):
        depositor=None
    return amount, depositor

def parse_sms_any(msg: str) -> tuple[int | None, str | None]:
    amount=None
    m=re.search(r"([0-9][0-9,]*)\s*원", msg or "")
    if m:
        raw=m.group(1).replace(",","")
        if raw.isdigit(): amount=int(raw)
    depositor=None
    for r in [re.compile(r"입금\s+[0-9,]+\s*원\s+([^\s\|]+)"),
              re.compile(r"입금자\s*[:\-]?\s*([^\s\|]+)"),
              re.compile(r"(보낸분|보낸이)\s*[:\-]?\s*([^\s\|]+)"),
              re.compile(r"\n([^\n\|]+)\s*(잔액|원|입금|$)")]:
        m=r.search(msg or "")
        if m:
            name=m.group(2) if (m.lastindex and m.lastindex>=2) else m.group(1)
            depositor=str(name).strip()
            break
    return amount, depositor

def parse_sms(msg: str) -> tuple[int | None, str | None]:
    a,d = parse_sms_kakaobank(msg)
    if a is None or d is None:
        a2,d2 = parse_sms_any(msg)
        if a is None: a=a2
        if d is None: d=d2
    return a,d

@app.post("/kbank-webhook")
async def kbank_webhook(req: Request):
    try:
        token=(req.headers.get("Authorization") or "").replace("Bearer","").strip()
        if token!=WEBHOOK_SECRET:
            return {"ok": False, "error":"unauthorized"}
        body=await req.json()
        gid=int(body.get("guildId") or body.get("server_id") or 0)
        msg=body.get("msg")
        amount=body.get("amount")
        depositor=body.get("depositor")
        if (amount is None or depositor is None) and isinstance(msg, str):
            a,d=parse_sms(msg)
            if amount is None: amount=a
            if depositor is None: depositor=d
        if not gid:
            return {"ok": False, "error":"guild_required"}
        guild=bot.get_guild(gid)
        if not guild:
            return {"ok": False, "error":"guild_not_found"}
        if amount is None or depositor is None:
            await send_log_text(guild, "admin", "[자동충전] 파싱 실패")
            return {"ok": False, "result":"parse_failed"}
        ok,msg2=await handle_deposit(guild, int(amount), str(depositor))
        return {"ok": ok, "result": msg2}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT","8787")), log_level="warning")

# ===== 부트 =====
async def guild_sync(b: commands.Bot):
    try:
        await b.tree.sync(guild=GUILD)
        print("[setup_hook] 길드 싱크 완료")
    except Exception as e:
        print(f"[setup_hook] 길드 싱크 실패: {e}")

@bot.event
async def setup_hook():
    await bot.add_cog(ControlCog(bot))
    await guild_sync(bot)

@bot.event
async def on_ready():
    print(f"로그인: {bot.user} (준비 완료)")
    t=threading.Thread(target=run_api, daemon=True)
    t.start()

TOKEN=os.getenv("DISCORD_TOKEN", "여기에_토큰_넣기")
bot.run(TOKEN)
