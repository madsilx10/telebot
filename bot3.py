import asyncio
import os
import re
import base64
import urllib.parse
import requests
from pyrogram import Client
from pyrogram.raw.functions.messages import RequestWebView

# ── Config ──────────────────────────────────────────────
API_ID      = 0
API_HASH    = ""
GEMINI_KEY  = ""   # isi Gemini API key
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

# ── Gemini Vision ─────────────────────────────────────────
def ask_gemini(soal_bytes, grid_bytes, btn_labels):
    soal_b64 = base64.standard_b64encode(soal_bytes).decode("utf-8")
    grid_b64 = base64.standard_b64encode(grid_bytes).decode("utf-8")

    btn_list = "\n".join([f"{i}: {label}" for i, label in enumerate(btn_labels)])

    prompt = f"""I have a CAPTCHA with two images:
1. First image: the QUESTION (shows a word or object name)
2. Second image: a 3x3 grid of emoji/icons to choose from

The emoji buttons available (index: emoji):
{btn_list}

Look at the QUESTION image and identify the object/word shown.
Then find which emoji in the grid matches.
Reply with ONLY the index number (0-8). Nothing else."""

    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}",
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{
                "parts": [
                    {"inline_data": {"mime_type": "image/jpeg", "data": soal_b64}},
                    {"inline_data": {"mime_type": "image/jpeg", "data": grid_b64}},
                    {"text": prompt}
                ]
            }]
        },
        timeout=15
    )

    if response.status_code == 200:
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        match = re.search(r'\d+', text)
        if match:
            return int(match.group())
    return None

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
async def run_account(session_string, index, bot_link, bot_username, x_profiles, quotes, posts, emails, wallets):
    x_profile = x_profiles[index-1] if index-1 < len(x_profiles) else ""
    quote     = quotes[index-1]     if index-1 < len(quotes)     else ""
    post      = posts[index-1]      if index-1 < len(posts)      else ""
    email     = emails[index-1]     if index-1 < len(emails)     else ""
    wallet    = wallets[index-1]    if index-1 < len(wallets)    else ""

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

        start_param = get_start_param(bot_link)
        try:
            await app.send_message(bot_username, f"/start {start_param}" if start_param else "/start")
            print(f"[+] Start")
            await asyncio.sleep(4)
        except Exception as e:
            print(f"[!] Start: {e}")
            return

        await click_keyboard(app, bot_username, ["join airdrop", "register"], "Join Airdrop Register")
        await click_keyboard(app, bot_username, ["registration"], "Registration")

        # Gemini Vision — cari soal + grid
        try:
            soal_bytes = None
            grid_msg   = None

            msgs = []
            async for msg in app.get_chat_history(bot_username, limit=10):
                msgs.append(msg)

            for msg in msgs:
                if msg.photo:
                    has_inline = msg.reply_markup and hasattr(msg.reply_markup, 'inline_keyboard')
                    if has_inline:
                        grid_msg = msg
                        # coba ambil soal dari foto grid itu sendiri juga
                        if soal_bytes is None:
                            photo_path = await app.download_media(msg.photo, in_memory=True)
                            soal_bytes = bytes(photo_path.getbuffer())
                    else:
                        photo_path = await app.download_media(msg.photo, in_memory=True)
                        soal_bytes = bytes(photo_path.getbuffer())

            if grid_msg:
                grid_path  = await app.download_media(grid_msg.photo, in_memory=True)
                grid_bytes = bytes(grid_path.getbuffer())

                all_btns = [
                    btn.text if hasattr(btn, 'text') else str(btn)
                    for row in grid_msg.reply_markup.inline_keyboard
                    for btn in row
                ]

                print(f"[~] Tanya Gemini...")
                idx = ask_gemini(soal_bytes, grid_bytes, all_btns)

                if idx is not None and 0 <= idx < len(all_btns):
                    cols = len(grid_msg.reply_markup.inline_keyboard[0])
                    await grid_msg.click(idx // cols, idx % cols)
                    print(f"[+] Pilih: {all_btns[idx]}")
                else:
                    print(f"[!] Gemini tidak bisa tentukan jawaban")
                await asyncio.sleep(2)
            else:
                print(f"[!] Grid tidak ditemukan")

        except Exception as e:
            print(f"[!] Captcha: {e}")

        await submit_text(app, bot_username, email,     "Submit email")
        await submit_text(app, bot_username, wallet,    "Submit wallet")
        await submit_text(app, bot_username, x_profile, "Submit X profile")
        await submit_text(app, bot_username, quote,     "Submit quote")
        await submit_text(app, bot_username, post,      "Submit post")

        await click_keyboard(app, bot_username, ["have joined", "i have"], "I Have Joined")
        await click_keyboard(app, bot_username, ["joined"], "Joined")

    print(f"[+] Akun {index} selesai")

# ── Main ─────────────────────────────────────────────────
async def main():
    sessions   = load_file("sessions.txt")
    x_profiles = load_file("x_profile.txt")
    quotes     = load_file("quote.txt")
    posts      = load_file("post.txt")
    emails     = load_file("email.txt")
    wallets    = load_file("wallet.txt")
    total      = len(sessions)

    print("""
+--------------------------------+
|                                |
|         AIRDROP BOT 3          |
|                                |
+--------------------------------+""")

    bot_link     = input("\nMasukkan link bot: ").strip()
    bot_username = extract_bot_username(bot_link)

    print(f"""
+--------------------------------+
| Bot   : @{bot_username:<22}|
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
        await run_account(sessions[i], i+1, bot_link, bot_username, x_profiles, quotes, posts, emails, wallets)
        if i != indices[-1]:
            print(f"\n[~] Delay {DELAY_BETWEEN_ACCOUNTS} detik...")
            await asyncio.sleep(DELAY_BETWEEN_ACCOUNTS)

    print("\n[+] Semua akun selesai!")

if __name__ == "__main__":
    asyncio.run(main())
