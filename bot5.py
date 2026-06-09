import asyncio
import os
import random
import string
import urllib.parse
from pyrogram import Client
from pyrogram.raw.functions.messages import RequestWebView

# ── Config ──────────────────────────────────────────────
API_ID   = 0
API_HASH = ""
BOT_LINK = "https://t.me/iTellerAirdropBot?start=r02624546911"
DELAY_BETWEEN_ACCOUNTS = 10

# ── Helpers ──────────────────────────────────────────────
def load_file(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return [line.strip() for line in f if line.strip()]

def extract_bot_username(link):
    link = link.strip()
    for prefix in ["https://t.me/", "http://t.me/", "t.me/"]:
        link = link.replace(prefix, "")
    return link.split("?")[0].strip("/")

def get_start_param(bot_link):
    if "?" in bot_link and "start=" in bot_link:
        return urllib.parse.parse_qs(bot_link.split("?")[1]).get("start", [""])[0]
    return ""

def extract_tme_links(text):
    import re
    return re.findall(r't\.me/([A-Za-z0-9_]+)', text or "")

def random_ig():
    name = ''.join(random.choices(string.ascii_lowercase, k=random.randint(6, 12)))
    return f"https://www.instagram.com/{name}/"

def random_fb():
    name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(6, 12)))
    return f"https://www.facebook.com/{name}"

def random_rt(x_username):
    tid = ''.join(random.choices(string.digits, k=19))
    return f"https://x.com/{x_username}/status/{tid}"

# ── Klik keyboard ────────────────────────────────────────
async def click_keyboard(app, bot_username, keywords, label):
    try:
        async for msg in app.get_chat_history(bot_username, limit=5):
            if msg.reply_markup and hasattr(msg.reply_markup, 'keyboard'):
                for row in msg.reply_markup.keyboard:
                    for btn in row:
                        txt = btn.text if hasattr(btn, 'text') else str(btn)
                        if any(k in txt.lower() for k in keywords):
                            await app.send_message(bot_username, txt)
                            print(f"[+] {label}")
                            await asyncio.sleep(3)
                            return True
    except Exception as e:
        print(f"[!] {label}: {e}")
    return False

async def submit_text(app, bot_username, text, label):
    if not text:
        return
    await app.send_message(bot_username, text)
    print(f"[+] {label}")
    await asyncio.sleep(2)

# ── Logic per akun ───────────────────────────────────────
async def run_account(session_string, index, x_usernames, wallets):
    bot_username = extract_bot_username(BOT_LINK)
    start_param  = get_start_param(BOT_LINK)

    x_username = x_usernames[index-1] if index-1 < len(x_usernames) else ""
    wallet     = wallets[index-1]     if index-1 < len(wallets)     else ""

    print(f"\n--- Akun {index} ---")

    async with Client(
        name=f"acc_{index}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_string,
        in_memory=True
    ) as app:
        me = await app.get_me()
        print(f"[@] @{me.username}")

        # Start bot
        try:
            await app.send_message(bot_username, f"/start {start_param}" if start_param else "/start")
            print(f"[+] Start")
            await asyncio.sleep(4)
        except Exception as e:
            print(f"[!] Start: {e}")
            return

        # Scan pesan — extract link t.me dan join channel
        try:
            joined = []
            async for msg in app.get_chat_history(bot_username, limit=10):
                links = extract_tme_links(msg.text or msg.caption or "")
                for username in links:
                    if username.lower() == bot_username.lower():
                        continue
                    if username in joined:
                        continue
                    try:
                        await app.join_chat(username)
                        print(f"[+] Join: @{username}")
                        joined.append(username)
                        await asyncio.sleep(2)
                    except Exception:
                        pass  # skip kalau udah join
        except Exception as e:
            print(f"[!] Join channel: {e}")

        # Klik Submit Details
        await click_keyboard(app, bot_username, ["submit details", "submit"], "Submit Details")

        # Isi username X
        if x_username:
            await submit_text(app, bot_username, x_username, "Username X")

        # Isi link IG random
        ig = random_ig()
        await submit_text(app, bot_username, ig, "Link IG")

        # Isi link FB random
        fb = random_fb()
        await submit_text(app, bot_username, fb, "Link FB")

        # Klik DONE
        await click_keyboard(app, bot_username, ["done"], "Done")

        # Isi link RT random
        rt = random_rt(x_username if x_username else "user")
        await submit_text(app, bot_username, rt, "Link RT")

        # Submit wallet
        if wallet:
            await submit_text(app, bot_username, wallet, "Submit wallet")

    print(f"[+] Akun {index} selesai")

# ── Main ─────────────────────────────────────────────────
async def main():
    sessions    = load_file("sessions.txt")
    x_usernames = load_file("x_username.txt")
    wallets     = load_file("wallet.txt")
    total       = len(sessions)

    print("""
+--------------------------------+
|                                |
|         AIRDROP BOT 5          |
|                                |
+--------------------------------+""")

    print(f"""
+--------------------------------+
| Bot   : @iTellerAirdropBot     |
| Akun  : {total:<22} |
+--------------------------------+
| 1. Semua akun                  |
| 2. Pilih satu akun             |
| 3. From akun ke-N              |
+--------------------------------+""")

    choice = input("\nPilih: ").strip()

    if choice == "1":
        indices = list(range(total))
    elif choice == "2":
        idx = int(input(f"Akun ke- (1-{total}): ")) - 1
        indices = [idx]
    elif choice == "3":
        start = int(input(f"Mulai dari akun ke- (1-{total}): ")) - 1
        indices = list(range(start, total))
    else:
        print("Pilihan tidak valid.")
        return

    for i in indices:
        await run_account(sessions[i], i+1, x_usernames, wallets)
        if i != indices[-1]:
            print(f"\n[~] Delay {DELAY_BETWEEN_ACCOUNTS} detik...")
            await asyncio.sleep(DELAY_BETWEEN_ACCOUNTS)

    print("\n[+] Semua akun selesai!")

if __name__ == "__main__":
    asyncio.run(main())
