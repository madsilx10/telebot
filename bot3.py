import asyncio
import os
import urllib.parse
import requests
from pyrogram import Client
from pyrogram.raw.functions.messages import RequestWebView

# ── ANSI Colors ──────────────────────────────────────────
R  = "\033[0m"
G  = "\033[92m"   # hijau
Y  = "\033[93m"   # kuning
RD = "\033[91m"   # merah
CY = "\033[96m"   # cyan
B  = "\033[94m"   # biru
DM = "\033[90m"   # abu

OK  = f"{G}[✓]{R}"
ERR = f"{RD}[✗]{R}"
INF = f"{CY}[~]{R}"
ACT = f"{Y}[>]{R}"
USR = f"{B}[@]{R}"

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

def match_button(ocr_text, buttons):
    ocr_text = ocr_text.lower()
    for i, btn in enumerate(buttons):
        if btn.lower() in ocr_text or ocr_text in btn.lower():
            return i
    for keyword in ocr_text.split():
        for i, btn in enumerate(buttons):
            if keyword in btn.lower():
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
                            print(f"  {OK} {label}")
                            await asyncio.sleep(3)
                            return True
    except Exception as e:
        print(f"  {ERR} {label}: {e}")
    return False

async def submit_text(app, bot_username, text, label):
    if not text:
        return
    await app.send_message(bot_username, text)
    print(f"  {OK} {label}")
    await asyncio.sleep(2)

# ── Core logic per akun ──────────────────────────────────
async def run_account(session_string, index, bot_link, bot_username, x_profiles, quotes, posts, emails, wallets):
    x_profile = x_profiles[index - 1] if index - 1 < len(x_profiles) else ""
    quote     = quotes[index - 1]     if index - 1 < len(quotes)     else ""
    post      = posts[index - 1]      if index - 1 < len(posts)      else ""
    email     = emails[index - 1]     if index - 1 < len(emails)     else ""
    wallet    = wallets[index - 1]    if index - 1 < len(wallets)    else ""

    print(f"\n{DM}{'─'*40}{R}")
    print(f"  {ACT} Akun {Y}{index}{R}")

    async with Client(
        name=f"acc_{index}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_string,
        in_memory=True
    ) as app:
        me = await app.get_me()
        print(f"  {USR} {CY}@{me.username}{R} {DM}({me.id}){R}")

        start_param = get_start_param(bot_link)
        try:
            msg_text = f"/start {start_param}" if start_param else "/start"
            await app.send_message(bot_username, msg_text)
            print(f"  {OK} Start")
            await asyncio.sleep(4)
        except Exception as e:
            print(f"  {ERR} Start gagal: {e}")
            return

        await click_keyboard(app, bot_username, ["join airdrop", "register"], "Join Airdrop Register")
        await click_keyboard(app, bot_username, ["registration"], "Registration")

        # Pilih gambar via OCR
        try:
            async for msg in app.get_chat_history(bot_username, limit=5):
                if msg.photo and msg.reply_markup and hasattr(msg.reply_markup, 'inline_keyboard'):
                    photo_path = await app.download_media(msg.photo, in_memory=True)
                    image_bytes = bytes(photo_path.getbuffer())
                    ocr_text = ocr_image_bytes(image_bytes)

                    all_btns = [
                        btn.text if hasattr(btn, 'text') else str(btn)
                        for row in msg.reply_markup.inline_keyboard
                        for btn in row
                    ]

                    btn_index = match_button(ocr_text, all_btns)
                    cols = len(msg.reply_markup.inline_keyboard[0])
                    await msg.click(btn_index // cols, btn_index % cols)
                    print(f"  {OK} Pilih gambar: {all_btns[btn_index]}")
                    await asyncio.sleep(2)
                    break
        except Exception as e:
            print(f"  {ERR} Pilih gambar: {e}")

        await submit_text(app, bot_username, email,     "Submit email")
        await submit_text(app, bot_username, wallet,    "Submit wallet")
        await submit_text(app, bot_username, x_profile, "Submit X profile")
        await submit_text(app, bot_username, quote,     "Submit quote")
        await submit_text(app, bot_username, post,      "Submit post")

        await click_keyboard(app, bot_username, ["have joined", "i have"], "I Have Joined")
        await click_keyboard(app, bot_username, ["joined"], "Joined")

    print(f"  {OK} {G}Selesai!{R}")

# ── Menu ─────────────────────────────────────────────────
async def main():
    sessions   = load_file("sessions.txt")
    x_profiles = load_file("x_profile.txt")
    quotes     = load_file("quote.txt")
    posts      = load_file("post.txt")
    emails     = load_file("email.txt")
    wallets    = load_file("wallet.txt")
    total      = len(sessions)

    print(f"""
{Y}+--------------------------------+
|         AIRDROP BOT 3          |
+--------------------------------+{R}""")

    bot_link     = input(f"\n{CY}Masukkan link bot:{R} ").strip()
    bot_username = extract_bot_username(bot_link)

    print(f"""
{Y}+--------------------------------+{R}
{Y}|{R} Bot   : {G}@{bot_username:<23}{Y}|{R}
{Y}|{R} Akun  : {G}{total:<23}{Y}|{R}
{Y}+--------------------------------+{R}
{Y}|{R} 1. Semua akun                  {Y}|{R}
{Y}|{R} 2. Pilih satu akun             {Y}|{R}
{Y}|{R} 3. From akun ke-N              {Y}|{R}
{Y}+--------------------------------+{R}""")

    choice = input(f"\n{CY}Pilih:{R} ").strip()

    if choice == "1":
        indices = list(range(total))
    elif choice == "2":
        idx = int(input(f"{CY}Akun ke- (1-{total}):{R} ")) - 1
        indices = [idx]
    elif choice == "3":
        start = int(input(f"{CY}Mulai dari akun ke- (1-{total}):{R} ")) - 1
        indices = list(range(start, total))
    else:
        print(f"{ERR} Pilihan tidak valid.")
        return

    for i in indices:
        await run_account(sessions[i], i + 1, bot_link, bot_username, x_profiles, quotes, posts, emails, wallets)
        if i != indices[-1]:
            print(f"\n  {INF} Delay {DELAY_BETWEEN_ACCOUNTS} detik...")
            await asyncio.sleep(DELAY_BETWEEN_ACCOUNTS)

    print(f"\n{G}  Semua akun selesai!{R}\n")

if __name__ == "__main__":
    asyncio.run(main())
