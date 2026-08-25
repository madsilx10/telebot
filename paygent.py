import asyncio, random, re
from pyrogram import Client
from pyrogram.raw import functions
from urllib.parse import urlparse, parse_qs, unquote
import aiohttp

def load(f): return open(f).read().splitlines()

sessions  = load("sessions.txt")
profiles  = load("x_profile.txt")
emails    = load("email.txt")
wallets   = load("wallet.txt")
apikeys   = load("apikey.txt")

BOT = "PaygentAirdropBot"
START = "ref_2005545171"

def gen_repost(profile_url):
    uname = profile_url.rstrip("/").split("/")[-1]
    sid = random.randint(1000000000000000000, 9999999999999999999)
    return f"https://x.com/{uname}/status/{sid}?s=20"

def solve_math(text):
    m = re.search(r'(\d+)\s*([+\-*/])\s*(\d+)', text or "")
    return str(eval(f"{m[1]}{m[2]}{m[3]}")) if m else None

async def click_btn(app, msg, keyword=None):
    for row in (msg.reply_markup.inline_keyboard if msg.reply_markup else []):
        for btn in row:
            if btn.callback_data:
                cb = btn.callback_data
                if keyword and keyword.lower() not in cb.lower(): continue
                await app.invoke(functions.messages.GetBotCallbackAnswer(
                    peer=await app.resolve_peer(BOT),
                    msg_id=msg.id,
                    data=cb.encode()
                ))
                return True
    return False

async def bypass_safeguard(app, msg):
    btn = msg.reply_markup.inline_keyboard[0][0]
    url = btn.web_app.url
    p = parse_qs(urlparse(url).query)
    me = await app.get_me()
    res = await app.invoke(functions.messages.RequestWebView(
        peer=await app.resolve_peer(msg.chat.id),
        bot=await app.resolve_peer(msg.from_user.id),
        url=url, platform="android"
    ))
    init_data = unquote(urlparse(res.url).fragment.split("tgWebAppData=")[1].split("&")[0])
    async with aiohttp.ClientSession() as s:
        r = await s.post("https://www.safeguard.run/api/verify", json={
            "token": True, "tglogin": init_data,
            "request_query": {
                "chat_id": p["chat_id"][0], "msg_id": int(p["msg_id"][0]),
                "hash": p["hash"][0], "portal": p.get("portal", ["yes"])[0],
                "signature": p["signature"][0], "timestamp": int(p["timestamp"][0]),
                "user_id": me.id, "user_firstname": me.first_name, "username": me.username,
            }
        }, headers={"Origin": "https://www.safeguard.run"})
        return await r.json()

async def wait_msg(app, timeout=10):
    await asyncio.sleep(timeout)
    async for msg in app.get_chat_history(BOT, limit=1):
        return msg

async def run(idx):
    profile = profiles[idx]
    app = Client(f"account_{idx}", session_string=sessions[idx])

    async with app:
        # /start
        await app.send_message(BOT, f"/start {START}")
        msg = await wait_msg(app)

        # Captcha math
        ans = solve_math(msg.text)
        if ans:
            await app.send_message(BOT, ans)
            msg = await wait_msg(app)

        # Join group / tap to verify buttons
        await click_btn(app, msg)
        msg = await wait_msg(app)

        # Safeguard mini app
        for row in (msg.reply_markup.inline_keyboard if msg.reply_markup else []):
            for btn in row:
                if hasattr(btn, "web_app") and btn.web_app:
                    await bypass_safeguard(app, msg)
                    await asyncio.sleep(3)

        msg = await wait_msg(app)

        # Submit Your Details
        await app.send_message(BOT, "Submit Your Details")
        await asyncio.sleep(2)

        for val in [profile, apikeys[idx], emails[idx]]:
            await app.send_message(BOT, val)
            await asyncio.sleep(1.5)

        msg = await wait_msg(app)
        await click_btn(app, msg)  # Done
        msg = await wait_msg(app)

        # Repost
        await app.send_message(BOT, gen_repost(profile))
        msg = await wait_msg(app)

        await click_btn(app, msg, keyword="yes")  # Yes
        msg = await wait_msg(app)

        # Wallet
        await app.send_message(BOT, wallets[idx])
        msg = await wait_msg(app)

        await click_btn(app, msg)  # Complete the airdrop

        print(f"[{idx}] Done ✓")

async def main():
    await asyncio.gather(*[run(i) for i in range(len(sessions))])

asyncio.run(main())
