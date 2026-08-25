import asyncio, random, re, os
from pyrogram import Client
from pyrogram.raw import functions
from urllib.parse import urlparse, parse_qs, unquote
import httpx

def load(f): return open(f).read().splitlines()

sessions  = load("sessions.txt")
profiles  = load("x_profile.txt")
emails    = load("email.txt")
wallets   = load("wallet.txt")
apikeys   = load("apikey.txt")

BOT   = "PaygentAirdropBot"
START = "ref_2005545171"

followed = set(open("followed.txt").read().splitlines()) if os.path.exists("followed.txt") else set()

def mark_followed(idx):
    followed.add(str(idx))
    open("followed.txt", "a").write(f"{idx}\n")

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
    async with httpx.AsyncClient() as s:
        r = await s.post("https://www.safeguard.run/api/verify", json={
            "token": True, "tglogin": init_data,
            "request_query": {
                "chat_id": p["chat_id"][0], "msg_id": int(p["msg_id"][0]),
                "hash": p["hash"][0], "portal": p.get("portal", ["yes"])[0],
                "signature": p["signature"][0], "timestamp": int(p["timestamp"][0]),
                "user_id": me.id, "user_firstname": me.first_name, "username": me.username,
            }
        }, headers={"Origin": "https://www.safeguard.run"})
        return r.json()

async def wait_msg(app, timeout=10):
    await asyncio.sleep(timeout)
    async for msg in app.get_chat_history(BOT, limit=1):
        return msg

async def run(idx):
    profile = profiles[idx]
    app = Client(f"account_{idx}", session_string=sessions[idx])

    async with app:
        await app.send_message(BOT, f"/start {START}")
        msg = await wait_msg(app)

        ans = solve_math(msg.text)
        if ans:
            await app.send_message(BOT, ans)
            msg = await wait_msg(app)

        await click_btn(app, msg)
        msg = await wait_msg(app)

        for row in (msg.reply_markup.inline_keyboard if msg.reply_markup else []):
            for btn in row:
                if hasattr(btn, "web_app") and btn.web_app:
                    await bypass_safeguard(app, msg)
                    await asyncio.sleep(3)

        msg = await wait_msg(app)

        # Skip follow kalau sudah
        if str(idx) not in followed:
            await click_btn(app, msg, keyword="follow")
            mark_followed(idx)
            msg = await wait_msg(app)

        await app.send_message(BOT, "Submit Your Details")
        await asyncio.sleep(2)

        for val in [profile, apikeys[idx], emails[idx]]:
            await app.send_message(BOT, val)
            await asyncio.sleep(1.5)

        msg = await wait_msg(app)
        await click_btn(app, msg)
        msg = await wait_msg(app)

        await app.send_message(BOT, gen_repost(profile))
        msg = await wait_msg(app)

        await click_btn(app, msg, keyword="yes")
        msg = await wait_msg(app)

        await app.send_message(BOT, wallets[idx])
        msg = await wait_msg(app)

        await click_btn(app, msg)

        print(f"[{idx}] Done ✓")

def select_accounts():
    total = len(sessions)
    print("
1 akun")
    print("semua")
    print("from x to end
")
    choice = input("> ").strip().lower()

    if choice == "1":
        idx = int(input("index: "))
        return [idx]
    elif choice == "2":
        return list(range(total))
    elif choice == "3":
        start = int(input("dari index: "))
        return list(range(start, total))

async def main(idxs):
    await asyncio.gather(*[run(i) for i in idxs])

if __name__ == "__main__":
    idxs = select_accounts()
    asyncio.run(main(idxs))
