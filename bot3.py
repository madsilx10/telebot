import asyncio
import os
import base64
import urllib.parse
import requests
from pyrogram import Client
from pyrogram.raw.functions.messages import RequestWebView

# ── Config ──────────────────────────────────────────────
API_ID   = 0        # isi 1x aja, sama buat semua akun
API_HASH = ""       # isi 1x aja, sama buat semua akun
OCR_API_KEY = ""    # isi API key OCR.space lu
DELAY_BETWEEN_ACCOUNTS = 10

# ── Load data ────────────────────────────────────────────
def load_file(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return [line.strip() for line in f if line.strip()]

def extract_bot_username(link):
    link = link.strip()
    link = link.replace("https://t.me/", "").replace("http://t.me/", "").replace("t.me/", "")
    username = link.split("?")[0].strip("/")
    return username

# ── OCR via OCR.space ────────────────────────────────────
def ocr_image_bytes(image_bytes):
    response = requests.post(
        "https://api.ocr.space/parse/image",
        files={"file": ("image.jpg", image_bytes, "image/jpeg")},
        data={"apikey": OCR_API_KEY, "language": "eng"}
    )
    if response.status_code == 200:
        result = response.json()
        parsed = result.get("ParsedResults", [])
        if parsed:
            return parsed[0].get("ParsedText", "").strip().lower()
    return ""

def match_button(ocr_text, buttons):
    ocr_text = ocr_text.lower()
    for i, btn_text in enumerate(buttons):
        if btn_text.lower() in ocr_text or ocr_text in btn_text.lower():
            return i
    keywords = ocr_text.split()
    for keyword in keywords:
        for i, btn_text in enumerate(buttons):
            if keyword in btn_text.lower():
                return i
    return 0

# ── Core logic per akun ──────────────────────────────────
async def run_account(session_string, index, bot_link, bot_username, x_profiles, quotes, posts, emails):
    print(f"\n{'='*50}")
    print(f"[Akun {index}] Mulai...")

    x_profile = x_profiles[index - 1] if index - 1 < len(x_profiles) else ""
    quote     = quotes[index - 1]     if index - 1 < len(quotes)     else ""
    post      = posts[index - 1]      if index - 1 < len(posts)      else ""
    email     = emails[index - 1]     if index - 1 < len(emails)     else ""

    async with Client(
        name=f"acc_{index}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_string,
        in_memory=True
    ) as app:
        me = await app.get_me()
        print(f"[Akun {index}] @{me.username} ({me.id})")

        # Start bot
        start_param = ""
        if "?" in bot_link and "start=" in bot_link:
            start_param = urllib.parse.parse_qs(bot_link.split("?")[1]).get("start", [""])[0]

        try:
            if start_param:
                await app.send_message(bot_username, f"/start {start_param}")
            else:
                await app.send_message(bot_username, "/start")
            print(f"[Akun {index}] ✅ Start")
        except Exception as e:
            print(f"[Akun {index}] ⚠️ Start gagal: {e}")

        await asyncio.sleep(4)

        # Klik "Join Airdrop Register"
        try:
            async for msg in app.get_chat_history(bot_username, limit=5):
                if msg.reply_markup and hasattr(msg.reply_markup, 'keyboard'):
                    for row in msg.reply_markup.keyboard:
                        for btn in row:
                            btn_text = btn.text if hasattr(btn, 'text') else str(btn)
                            if any(k in btn_text.lower() for k in ["join airdrop", "register"]):
                                await app.send_message(bot_username, btn_text)
                                print(f"[Akun {index}] ✅ {btn_text}")
                                await asyncio.sleep(3)
                                break
        except Exception as e:
            print(f"[Akun {index}] ⚠️ Join Airdrop: {e}")

        # Klik "Registration"
        try:
            async for msg in app.get_chat_history(bot_username, limit=5):
                if msg.reply_markup and hasattr(msg.reply_markup, 'keyboard'):
                    for row in msg.reply_markup.keyboard:
                        for btn in row:
                            btn_text = btn.text if hasattr(btn, 'text') else str(btn)
                            if "registration" in btn_text.lower():
                                await app.send_message(bot_username, btn_text)
                                print(f"[Akun {index}] ✅ {btn_text}")
                                await asyncio.sleep(3)
                                break
        except Exception as e:
            print(f"[Akun {index}] ⚠️ Registration: {e}")

        # Pilih gambar/emoji via OCR
        try:
            async for msg in app.get_chat_history(bot_username, limit=5):
                if msg.photo and msg.reply_markup and hasattr(msg.reply_markup, 'inline_keyboard'):
                    photo_path = await app.download_media(msg.photo, in_memory=True)
                    image_bytes = bytes(photo_path.getbuffer())

                    ocr_text = ocr_image_bytes(image_bytes)
                    print(f"[Akun {index}] 🔍 OCR: '{ocr_text}'")

                    all_btns = []
                    for row in msg.reply_markup.inline_keyboard:
                        for btn in row:
                            all_btns.append(btn.text if hasattr(btn, 'text') else str(btn))

                    btn_index = match_button(ocr_text, all_btns)
                    row_idx = btn_index // max(len(msg.reply_markup.inline_keyboard[0]), 1)
                    col_idx = btn_index % max(len(msg.reply_markup.inline_keyboard[0]), 1)

                    await msg.click(row_idx, col_idx)
                    print(f"[Akun {index}] ✅ Pilih: {all_btns[btn_index]}")
                    await asyncio.sleep(2)
                    break
        except Exception as e:
            print(f"[Akun {index}] ⚠️ Pilih gambar: {e}")

        # Submit email
        if email:
            await app.send_message(bot_username, email)
            print(f"[Akun {index}] ✅ Submit email")
            await asyncio.sleep(2)

        # Submit X profile
        if x_profile:
            await app.send_message(bot_username, x_profile)
            print(f"[Akun {index}] ✅ Submit X profile")
            await asyncio.sleep(2)

        # Submit quote
        if quote:
            await app.send_message(bot_username, quote)
            print(f"[Akun {index}] ✅ Submit quote")
            await asyncio.sleep(2)

        # Submit post
        if post:
            await app.send_message(bot_username, post)
            print(f"[Akun {index}] ✅ Submit post")
            await asyncio.sleep(2)

        # Klik "I have joined"
        try:
            async for msg in app.get_chat_history(bot_username, limit=5):
                if msg.reply_markup and hasattr(msg.reply_markup, 'keyboard'):
                    for row in msg.reply_markup.keyboard:
                        for btn in row:
                            btn_text = btn.text if hasattr(btn, 'text') else str(btn)
                            if "have joined" in btn_text.lower() or "i have" in btn_text.lower():
                                await app.send_message(bot_username, btn_text)
                                print(f"[Akun {index}] ✅ {btn_text}")
                                await asyncio.sleep(2)
                                break
        except Exception as e:
            print(f"[Akun {index}] ⚠️ I have joined: {e}")

        # Klik "Joined"
        try:
            async for msg in app.get_chat_history(bot_username, limit=5):
                if msg.reply_markup and hasattr(msg.reply_markup, 'keyboard'):
                    for row in msg.reply_markup.keyboard:
                        for btn in row:
                            btn_text = btn.text if hasattr(btn, 'text') else str(btn)
                            if btn_text.lower().strip() == "joined":
                                await app.send_message(bot_username, btn_text)
                                print(f"[Akun {index}] ✅ {btn_text}")
                                await asyncio.sleep(2)
                                break
        except Exception as e:
            print(f"[Akun {index}] ⚠️ Joined: {e}")

    print(f"[Akun {index}] ✅ Selesai!")

# ── Menu ─────────────────────────────────────────────────
async def main():
    sessions   = load_file("sessions.txt")
    x_profiles = load_file("x_profile.txt")
    quotes     = load_file("quote.txt")
    posts      = load_file("post.txt")
    emails     = load_file("email.txt")
    total      = len(sessions)

    bot_link = input("Link bot: ").strip()
    bot_username = extract_bot_username(bot_link)

    print(f"""
╔══════════════════════════════╗
║       @{bot_username:<22}║
╠══════════════════════════════╣
║  Total akun: {total:<17}║
╠══════════════════════════════╣
║  1. Semua akun               ║
║  2. Pilih satu akun          ║
║  3. From akun ke-N           ║
╚══════════════════════════════╝""")

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
        await run_account(sessions[i], i + 1, bot_link, bot_username, x_profiles, quotes, posts, emails)
        if i != indices[-1]:
            print(f"\n⏳ Delay {DELAY_BETWEEN_ACCOUNTS} detik...")
            await asyncio.sleep(DELAY_BETWEEN_ACCOUNTS)

    print("\n✅ Semua akun selesai!")

if __name__ == "__main__":
    asyncio.run(main())
