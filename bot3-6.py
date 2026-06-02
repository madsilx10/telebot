import asyncio
import os
import urllib.parse
import requests
from pyrogram import Client
from pyrogram.raw.functions.messages import RequestWebView

# ── Config ──────────────────────────────────────────────
API_ID      = 0
API_HASH    = ""
OCR_API_KEY = ""
DELAY_BETWEEN_ACCOUNTS = 10

# ── Load data ────────────────────────────────────────────
def load_file(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return [line.strip() for line in f if line.strip()]

def load_mapping():
    mapping = {}
    if not os.path.exists("mapping.txt"):
        return mapping
    with open("mapping.txt", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if ":" in line:
                key, val = line.split(":", 1)
                mapping[key.strip().lower()] = val.strip()
    return mapping

def extract_bot_username(link):
    link = link.strip()
    link = link.replace("https://t.me/", "").replace("http://t.me/", "").replace("t.me/", "")
    return link.split("?")[0].strip("/")

def get_start_param(bot_link):
    if "?" in bot_link and "start=" in bot_link:
        return urllib.parse.parse_qs(bot_link.split("?")[1]).get("start", [""])[0]
    return ""

# ── OCR via OCR.space ────────────────────────────────────
def ocr_image_bytes(image_bytes):
    response = requests.post(
        "https://api.ocr.space/parse/image",
        files={"file": ("image.jpg", image_bytes, "image/jpeg")},
        data={"apikey": OCR_API_KEY, "language": "eng"}
    )
    if response.status_code == 200:
        parsed = response.json().get("ParsedResults", [])
        if parsed:
            return parsed[0].get("ParsedText", "").strip().lower()
    return ""

def find_emoji_from_ocr(ocr_text, mapping):
    ocr_text = ocr_text.lower().strip()
    # coba exact match dulu
    for key, emoji in mapping.items():
        if key in ocr_text:
            return emoji
    # fallback keyword per kata
    for word in ocr_text.split():
        for key, emoji in mapping.items():
            if word in key or key in word:
                return emoji
    return None

def match_button_by_emoji(target_emoji, buttons):
    for i, btn in enumerate(buttons):
        if target_emoji in btn:
            return i
    return 0

# ── Klik keyboard button ─────────────────────────────────
async def click_keyboard(app, bot_username, keywords, label):
    try:
        async for msg in app.get_chat_history(bot_username, limit=5):
            if msg.reply_markup and hasattr(msg.reply_markup, 'keyboard'):
                for row in msg.reply_markup.keyboard:
                    for btn in row:
                        btn_text = btn.text if hasattr(btn, 'text') else str(btn)
                        if any(k in btn_text.lower() for k in keywords):
                            await app.send_message(bot_username, btn_text)
                            print(f"[+] {label}")
                            await asyncio.sleep(3)
                            return True
    except Exception as e:
        print(f"[!] {label} gagal: {e}")
    return False

async def submit_text(app, bot_username, text, label):
    if not text:
        return
    await app.send_message(bot_username, text)
    print(f"[+] {label}")
    await asyncio.sleep(2)

# ── Core logic per akun ──────────────────────────────────
async def run_account(session_string, index, bot_link, bot_username, x_profiles, quotes, posts, emails, wallets, mapping):
    x_profile = x_profiles[index - 1] if index - 1 < len(x_profiles) else ""
    quote     = quotes[index - 1]     if index - 1 < len(quotes)     else ""
    post      = posts[index - 1]      if index - 1 < len(posts)      else ""
    email     = emails[index - 1]     if index - 1 < len(emails)     else ""
    wallet    = wallets[index - 1]    if index - 1 < len(wallets)    else ""

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
            msg_text = f"/start {start_param}" if start_param else "/start"
            await app.send_message(bot_username, msg_text)
            print(f"[+] Start")
            await asyncio.sleep(4)
        except Exception as e:
            print(f"[!] Start gagal: {e}")
            return

        await click_keyboard(app, bot_username, ["join airdrop", "register"], "Join Airdrop Register")
        await click_keyboard(app, bot_username, ["registration"], "Registration")

        # Baca soal + klik emoji — 1 pesan berisi photo + inline_keyboard
        try:
            async for msg in app.get_chat_history(bot_username, limit=5):
                if msg.photo and msg.reply_markup and hasattr(msg.reply_markup, 'inline_keyboard'):
                    photo_path  = await app.download_media(msg.photo, in_memory=True)
                    image_bytes = bytes(photo_path.getbuffer())
                    soal_text   = ocr_image_bytes(image_bytes)
                    print(f"[~] Soal: {soal_text}")

                    all_btns = [
                        btn.text if hasattr(btn, 'text') else str(btn)
                        for row in msg.reply_markup.inline_keyboard
                        for btn in row
                    ]

                    target_emoji = find_emoji_from_ocr(soal_text, mapping)
                    if target_emoji:
                        btn_index = match_button_by_emoji(target_emoji, all_btns)
                        cols = len(msg.reply_markup.inline_keyboard[0])
                        await msg.click(btn_index // cols, btn_index % cols)
                        print(f"[+] Pilih: {all_btns[btn_index]}")
                    else:
                        print(f"[!] Emoji tidak ditemukan untuk: {soal_text}")
                    await asyncio.sleep(2)
                    break

        except Exception as e:
            print(f"[!] Pilih gambar gagal: {e}")

        await submit_text(app, bot_username, email,     "Submit email")
        await submit_text(app, bot_username, wallet,    "Submit wallet")
        await submit_text(app, bot_username, x_profile, "Submit X profile")
        await submit_text(app, bot_username, quote,     "Submit quote")
        await submit_text(app, bot_username, post,      "Submit post")

        await click_keyboard(app, bot_username, ["have joined", "i have"], "I Have Joined")
        await click_keyboard(app, bot_username, ["joined"], "Joined")

    print(f"[✓] Akun {index} selesai")

# ── Menu ─────────────────────────────────────────────────
async def main():
    sessions   = load_file("sessions.txt")
    x_profiles = load_file("x_profile.txt")
    quotes     = load_file("quote.txt")
    posts      = load_file("post.txt")
    emails     = load_file("email.txt")
    wallets    = load_file("wallet.txt")
    mapping    = load_mapping()
    total      = len(sessions)

    print("""
+---------------------------+
|       AIRDROP BOT 3       |
+---------------------------+""")

    bot_link     = input("\nMasukkan link bot: ").strip()
    bot_username = extract_bot_username(bot_link)

    print(f"""
+---------------------------+
| Bot   : @{bot_username:<17}|
| Akun  : {total:<17} |
+---------------------------+
| 1. Semua akun             |
| 2. Pilih satu akun        |
| 3. From akun ke-N         |
+---------------------------+""")

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
        await run_account(sessions[i], i + 1, bot_link, bot_username, x_profiles, quotes, posts, emails, wallets, mapping)
        if i != indices[-1]:
            print(f"\n[~] Delay {DELAY_BETWEEN_ACCOUNTS} detik...")
            await asyncio.sleep(DELAY_BETWEEN_ACCOUNTS)

    print("\n[✓] Semua akun selesai!")

if __name__ == "__main__":
    asyncio.run(main())
