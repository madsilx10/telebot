import asyncio
import os
import re
import urllib.parse
import requests
from difflib import SequenceMatcher
from pyrogram import Client
from pyrogram.raw.functions.messages import RequestWebView

# ── Config ──────────────────────────────────────────────
API_ID      = 0
API_HASH    = ""
OCR_API_KEY = ""
DELAY_BETWEEN_ACCOUNTS = 10

# ── Helpers ──────────────────────────────────────────────
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
    for prefix in ["https://t.me/", "http://t.me/", "t.me/"]:
        link = link.replace(prefix, "")
    return link.split("?")[0].strip("/")

def get_start_param(bot_link):
    if "?" in bot_link and "start=" in bot_link:
        return urllib.parse.parse_qs(bot_link.split("?")[1]).get("start", [""])[0]
    return ""

# ── OCR ──────────────────────────────────────────────────
def ocr_image_bytes(image_bytes):
    try:
        r = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file": ("image.jpg", image_bytes, "image/jpeg")},
            data={"apikey": OCR_API_KEY, "language": "eng"},
            timeout=10
        )
        if r.status_code == 200:
            parsed = r.json().get("ParsedResults", [])
            if parsed:
                text = parsed[0].get("ParsedText", "").strip().lower()
                text = re.sub(r'[^a-z0-9 ]', '', text).strip()
                return text
    except Exception:
        pass
    return ""

def find_emoji(ocr_text, mapping):
    ocr_text = ocr_text.lower().strip()

    # exact / substring match
    for key, emoji in mapping.items():
        if key in ocr_text or ocr_text in key:
            return emoji

    # fuzzy match per kata
    best_emoji, best_score = None, 0.0
    for word in ocr_text.split():
        for key, emoji in mapping.items():
            score = SequenceMatcher(None, word, key).ratio()
            if score > best_score:
                best_score = score
                best_emoji = emoji

    return best_emoji if best_score >= 0.6 else None

def find_btn_index(target_emoji, buttons):
    for i, btn in enumerate(buttons):
        if target_emoji in btn:
            return i
    return 0

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
async def run_account(session_string, index, bot_link, bot_username, x_profiles, quotes, posts, emails, wallets, mapping):
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

        # Start
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

        # OCR soal + pilih emoji
        # Soal dan grid ada di 2 pesan berbeda — soal = photo tanpa inline keyboard, grid = photo dengan inline keyboard
        try:
            soal_text = ""
            grid_msg  = None

            msgs = []
            async for msg in app.get_chat_history(bot_username, limit=10):
                msgs.append(msg)

            # cari soal (photo tanpa inline keyboard) dan grid (photo dengan inline keyboard)
            for msg in msgs:
                if msg.photo:
                    has_inline = msg.reply_markup and hasattr(msg.reply_markup, 'inline_keyboard')
                    if has_inline:
                        grid_msg = msg
                    else:
                        # ini soal
                        photo_path  = await app.download_media(msg.photo, in_memory=True)
                        image_bytes = bytes(photo_path.getbuffer())
                        soal_text   = ocr_image_bytes(image_bytes)
                        print(f"[~] Soal: '{soal_text}'")

            # kalau soal kosong, coba baca caption grid
            if not soal_text and grid_msg and grid_msg.caption:
                soal_text = grid_msg.caption.lower().strip()
                print(f"[~] Soal (caption): '{soal_text}'")

            if grid_msg:
                all_btns = [
                    btn.text if hasattr(btn, 'text') else str(btn)
                    for row in grid_msg.reply_markup.inline_keyboard
                    for btn in row
                ]

                if soal_text:
                    target = find_emoji(soal_text, mapping)
                    if target:
                        idx  = find_btn_index(target, all_btns)
                        cols = len(grid_msg.reply_markup.inline_keyboard[0])
                        await grid_msg.click(idx // cols, idx % cols)
                        print(f"[+] Pilih: {all_btns[idx]}")
                    else:
                        print(f"[!] Emoji tidak ditemukan untuk: '{soal_text}'")
                else:
                    print(f"[!] Soal tidak terbaca")
                await asyncio.sleep(2)
            else:
                print(f"[!] Grid emoji tidak ditemukan")

        except Exception as e:
            print(f"[!] Pilih gambar: {e}")

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
    mapping    = load_mapping()
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
        await run_account(sessions[i], i+1, bot_link, bot_username, x_profiles, quotes, posts, emails, wallets, mapping)
        if i != indices[-1]:
            print(f"\n[~] Delay {DELAY_BETWEEN_ACCOUNTS} detik...")
            await asyncio.sleep(DELAY_BETWEEN_ACCOUNTS)

    print("\n[+] Semua akun selesai!")

if __name__ == "__main__":
    asyncio.run(main())
