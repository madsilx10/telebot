import asyncio, random, re, os
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler          # FIX: import yang hilang
from pyrogram.raw import functions
from urllib.parse import urlparse, parse_qs, unquote
import httpx

# ─── Config ────────────────────────────────────────────────────────────────
def load(f): return open(f).read().splitlines()

sessions = load("sessions.txt")
profiles = load("x_profile.txt")
emails   = load("email.txt")
wallets  = load("wallet.txt")
apikeys  = load("apikey.txt")

API_ID   = 123456
API_HASH = "your_api_hash"

BOT   = "PaygentAirdropBot"
START = "ref_2005545171"

followed = set(open("followed.txt").read().splitlines()) if os.path.exists("followed.txt") else set()

# ─── Helpers ────────────────────────────────────────────────────────────────
def log(idx, msg):
    print(f"  [{idx:>3}] {msg}")

def mark_followed(idx):
    followed.add(str(idx))
    with open("followed.txt", "a") as f:     # FIX: pakai with agar file ter-close
        f.write(f"{idx}\n")

def gen_repost(profile_url):
    uname = profile_url.rstrip("/").split("/")[-1]
    sid = random.randint(1000000000000000000, 9999999999999999999)
    return f"https://x.com/{uname}/status/{sid}?s=20"

def solve_math(text):
    m = re.search(r'(\d+)\s*([+\-*/])\s*(\d+)', text or "")
    return str(eval(f"{m[1]}{m[2]}{m[3]}")) if m else None

# ─── Bot Interaction ─────────────────────────────────────────────────────────
async def click_btn(app, msg, keyword=None):
    for row in (msg.reply_markup.inline_keyboard if msg.reply_markup and hasattr(msg.reply_markup, "inline_keyboard") else []):
        for btn in row:
            if not btn.callback_data: continue
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
    p   = parse_qs(urlparse(url).query)
    me  = await app.get_me()

    # FIX: msg.from_user bisa None (pesan dari channel/anonymous)
    bot_peer = (
        await app.resolve_peer(msg.from_user.id)
        if msg.from_user else
        await app.resolve_peer(BOT)
    )

    res = await app.invoke(functions.messages.RequestWebView(
        peer=await app.resolve_peer(msg.chat.id),
        bot=bot_peer,
        url=url, platform="android"
    ))
    init_data = unquote(urlparse(res.url).fragment.split("tgWebAppData=")[1].split("&")[0])

    async with httpx.AsyncClient() as s:
        r = await s.post("https://www.safeguard.run/api/verify", json={
            "token": True, "tglogin": init_data,
            "request_query": {
                "chat_id":        p["chat_id"][0],
                "msg_id":         int(p["msg_id"][0]),
                "hash":           p["hash"][0],
                "portal":         p.get("portal", ["yes"])[0],
                "signature":      p["signature"][0],
                "timestamp":      int(p["timestamp"][0]),
                "user_id":        me.id,
                "user_firstname": me.first_name,
                "username":       me.username,
            }
        }, headers={"Origin": "https://www.safeguard.run"})
        return r.json()

async def wait_msg(app, timeout=30):
    # FIX: get_event_loop() deprecated Python 3.10+ → pakai get_running_loop()
    loop   = asyncio.get_running_loop()
    future = loop.create_future()

    async def _handler(client, message):
        if not future.done():
            future.set_result(message)

    # FIX: add_handler() return tuple (handler, group) — harus di-unpack
    # kalau tidak di-unpack, remove_handler() cari tuple-nya di list → ValueError
    handler, group = app.add_handler(
        MessageHandler(_handler, filters.chat(BOT) & filters.incoming)
    )

    try:
        return await asyncio.wait_for(future, timeout=timeout)
    except asyncio.TimeoutError:
        async for msg in app.get_chat_history(BOT, limit=1):
            return msg
    finally:
        # pass group juga agar dispatcher tahu di bucket mana handler-nya
        app.remove_handler(handler, group)

# ─── Runner Per Akun ─────────────────────────────────────────────────────────
async def run(idx):
    profile = profiles[idx]
    app = Client(f"account_{idx}", api_id=API_ID, api_hash=API_HASH, session_string=sessions[idx])

    try:
        async with app:
            log(idx, "Starting...")

            await app.send_message(BOT, f"/start {START}")
            msg = await wait_msg(app)

            ans = solve_math(msg.text)
            if ans:
                log(idx, f"Math: {msg.text.strip()} → {ans}")
                await app.send_message(BOT, ans)
                msg = await wait_msg(app)

            await click_btn(app, msg)
            msg = await wait_msg(app)

            for row in (msg.reply_markup.inline_keyboard if msg.reply_markup and hasattr(msg.reply_markup, "inline_keyboard") else []):
                for btn in row:
                    if hasattr(btn, "web_app") and btn.web_app:
                        log(idx, "Bypassing safeguard...")
                        await bypass_safeguard(app, msg)
                        await asyncio.sleep(3)

            msg = await wait_msg(app)

            if str(idx) not in followed:
                log(idx, "Following...")
                await click_btn(app, msg, keyword="follow")
                mark_followed(idx)
                msg = await wait_msg(app)
            else:
                log(idx, "Already followed, skip.")

            log(idx, "Submitting details...")
            await app.send_message(BOT, "Submit Your Details")
            await asyncio.sleep(2)

            for val in [profile, apikeys[idx], emails[idx]]:
                await app.send_message(BOT, val)
                await asyncio.sleep(1.5)

            msg = await wait_msg(app)
            await click_btn(app, msg)
            msg = await wait_msg(app)

            log(idx, "Sending repost...")
            await app.send_message(BOT, gen_repost(profile))
            msg = await wait_msg(app)

            await click_btn(app, msg, keyword="yes")
            msg = await wait_msg(app)

            log(idx, f"Wallet: {wallets[idx][:8]}...")
            await app.send_message(BOT, wallets[idx])
            msg = await wait_msg(app)

            await click_btn(app, msg)

            log(idx, "✓ Done!")

    except Exception as e:
        # FIX: tangkap error per akun agar akun lain tetap jalan
        log(idx, f"✗ Error: {e}")

# ─── Account Selector ─────────────────────────────────────────────────────────
def select_accounts():
    total = len(sessions)
    print()
    print("┌───────────────────────────────────┐")
    print("│     Paygent Airdrop Bot  v6       │")
    print("├───────────────────────────────────┤")
    print(f"│  Total akun : {total:<21}│")
    print("├───────────────────────────────────┤")
    print("│  [1] Satu akun                    │")
    print("│  [2] Semua akun                   │")
    print("│  [3] Dari index X sampai akhir    │")
    print("└───────────────────────────────────┘")

    # FIX: loop validasi — sebelumnya return None kalau input invalid → crash
    while True:
        choice = input("  Pilih > ").strip()

        if choice == "1":
            try:
                idx = int(input("  Index akun : ").strip())
                if 0 <= idx < total:
                    return [idx]
                print(f"  ✗ Index harus 0–{total - 1}")
            except ValueError:
                print("  ✗ Masukkan angka yang valid.")

        elif choice == "2":
            return list(range(total))

        elif choice == "3":
            try:
                start = int(input(f"  Dari index (0–{total - 1}) : ").strip())
                if 0 <= start < total:
                    return list(range(start, total))
                print(f"  ✗ Index harus 0–{total - 1}")
            except ValueError:
                print("  ✗ Masukkan angka yang valid.")

        else:
            print("  ✗ Pilihan tidak valid. Masukkan 1, 2, atau 3.")

async def main(idxs):
    print(f"\n  ▶ Menjalankan {len(idxs)} akun...\n")
    await asyncio.gather(*[run(i) for i in idxs])
    print("\n  ✓ Semua akun selesai.")

if __name__ == "__main__":
    idxs = select_accounts()
    asyncio.run(main(idxs))
