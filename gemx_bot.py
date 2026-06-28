import asyncio
import re
import os
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.errors import FloodWait, UserAlreadyParticipant, InviteHashExpired

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BOT_USERNAME = "GemXAppBot"
START_PARAM  = "2005545171"
SESSION_FILE = "sessions.txt"
CHANNEL_FILE = "channels.txt"
API_ID       = 0       # isi API_ID lo
API_HASH     = ""      # isi API_HASH lo
DELAY        = 3
# ──────────────────────────────────────────────────────────────────────────────

def banner():
    print("+─────────────────────────────────────────+")
    print("|           GemX Farming Bot              |")
    print("|        Pyrogram Multi-Account           |")
    print("+─────────────────────────────────────────+")

def load_sessions():
    sessions = []
    if not os.path.exists(SESSION_FILE):
        print(f"[!] {SESSION_FILE} tidak ditemukan")
        return sessions
    with open(SESSION_FILE) as f:
        for i, line in enumerate(f, 1):
            token = line.strip()
            if token:
                sessions.append((i, token))  # (nomor, token_string)
    return sessions

def parse_chat_link(link: str) -> str:
    """Convert https://t.me/xxx atau https://t.me/+xxx jadi format yang diterima join_chat."""
    link = link.strip()
    if link.startswith("https://t.me/+") or link.startswith("https://t.me/joinchat/"):
        return link  # invite link, langsung pass
    if link.startswith("https://t.me/"):
        return "@" + link.split("https://t.me/")[-1].strip("/")
    if not link.startswith("@"):
        return "@" + link
    return link

def load_channels():
    channels = []
    if not os.path.exists(CHANNEL_FILE):
        print(f"[!] {CHANNEL_FILE} tidak ditemukan, skip join channel")
        return channels
    with open(CHANNEL_FILE) as f:
        for line in f:
            ch = line.strip()
            if ch:
                channels.append(ch)
    return channels

def solve_captcha(text: str):
    match = re.search(r'(\d+)\s*([\+\-\*\/x×÷])\s*(\d+)', text)
    if not match:
        return None
    a, op, b = int(match.group(1)), match.group(2), int(match.group(3))
    if op in ('*', 'x', '×'):
        return str(a * b)
    elif op == '+':
        return str(a + b)
    elif op == '-':
        return str(a - b)
    elif op in ('/', '÷'):
        if b == 0:
            return None
        result = a / b
        return str(int(result) if result == int(result) else round(result, 2))
    return None

async def join_channels(client: Client, channels: list):
    for ch in channels:
        try:
            await client.join_chat(parse_chat_link(ch))
            print(f"  [+] Joined: {ch}")
        except UserAlreadyParticipant:
            print(f"  [=] Already joined: {ch}")
        except InviteHashExpired:
            print(f"  [!] Link expired: {ch}")
        except FloodWait as e:
            print(f"  [~] FloodWait {e.value}s, nunggu...")
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"  [!] Gagal join {ch}: {e}")
        await asyncio.sleep(DELAY)

async def click_button(app: Client, msg: Message, keyword: str):
    if not msg.reply_markup:
        return False
    markup = msg.reply_markup

    # InlineKeyboardMarkup
    if hasattr(markup, "inline_keyboard"):
        for row in markup.inline_keyboard:
            for btn in row:
                if keyword.lower() in btn.text.lower():
                    await msg.click(btn.text)
                    print(f"  [+] Klik inline: {btn.text}")
                    return True

    # ReplyKeyboardMarkup — harus kirim teks biasa
    if hasattr(markup, "keyboard"):
        for row in markup.keyboard:
            for btn in row:
                text = btn.text if hasattr(btn, "text") else str(btn)
                if keyword.lower() in text.lower():
                    await app.send_message(msg.chat.id, text)
                    print(f"  [+] Klik reply keyboard: {text}")
                    return True

    return False

async def run_account(idx: int, token: str, channels: list):
    print(f"\n[*] Akun #{idx}")

    async with Client(
        name=f"acct_{idx}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=token
    ) as app:
        me = await app.get_me()
        print(f"  [+] Login: {me.first_name} (@{me.username})")

        # 1. Join channels
        if channels:
            print(f"  [*] Join {len(channels)} channel...")
            await join_channels(app, channels)

        # 2. /start dengan referral
        print(f"  [*] /start ke @{BOT_USERNAME} (ref: {START_PARAM})")
        try:
            await app.send_message(BOT_USERNAME, f"/start {START_PARAM}")
        except FloodWait as e:
            print(f"  [~] FloodWait {e.value}s, nunggu...")
            await asyncio.sleep(e.value)
            await app.send_message(BOT_USERNAME, f"/start {START_PARAM}")

        await asyncio.sleep(DELAY)

        # 3. Ambil pesan dari bot, cari captcha
        msgs = []
        async for m in app.get_chat_history(BOT_USERNAME, limit=5):
            msgs.append(m)

        captcha_solved = False
        for msg in msgs:
            if msg.from_user and msg.from_user.username and \
               msg.from_user.username.lower() == BOT_USERNAME.lower():
                text = msg.text or msg.caption or ""
                answer = solve_captcha(text)
                if answer and not captcha_solved:
                    print(f"  [*] Captcha: {text.strip()!r} => {answer}")
                    await app.send_message(BOT_USERNAME, answer)
                    captcha_solved = True
                    await asyncio.sleep(DELAY)
                    break

        # 4. Klik tombol Check
        await asyncio.sleep(DELAY)
        async for msg in app.get_chat_history(BOT_USERNAME, limit=5):
            if msg.reply_markup:
                if await click_button(app, msg, "check"):
                    await asyncio.sleep(DELAY)
                    break

        # 5. Klik tombol GemX Box
        await asyncio.sleep(DELAY)
        async for msg in app.get_chat_history(BOT_USERNAME, limit=5):
            if msg.reply_markup:
                clicked = await click_button(app, msg, "gemx box")
                if not clicked:
                    clicked = await click_button(app, msg, "box")
                if clicked:
                    await asyncio.sleep(DELAY)
                    break

        print(f"  [+] Selesai akun #{idx}")

async def main():
    banner()
    sessions = load_sessions()
    channels = load_channels()

    if not sessions:
        print("[!] Tidak ada sesi ditemukan di sessions.txt")
        return

    print(f"\n[*] Total akun: {len(sessions)}")
    print("\nPilih mode:")
    print("  1. Satu akun")
    print("  2. Semua akun")
    print("  3. Dari akun X sampai akhir")
    choice = input("\nPilihan (1/2/3): ").strip()

    if choice == "1":
        print("\nDaftar akun:")
        for i, _ in sessions:
            print(f"  {i}. Akun #{i}")
        idx = int(input("Pilih nomor: ").strip())
        target = [(i, t) for i, t in sessions if i == idx]

    elif choice == "2":
        target = sessions

    elif choice == "3":
        print("\nDaftar akun:")
        for i, _ in sessions:
            print(f"  {i}. Akun #{i}")
        start = int(input("Dari nomor: ").strip())
        target = [(i, t) for i, t in sessions if i >= start]

    else:
        print("[!] Pilihan tidak valid")
        return

    print(f"\n[*] Menjalankan {len(target)} akun...\n")
    for idx, token in target:
        try:
            await run_account(idx, token, channels)
        except Exception as e:
            print(f"  [!] Error akun #{idx}: {e}")
        await asyncio.sleep(2)

    print("\n[+] Semua akun selesai.")

if __name__ == "__main__":
    asyncio.run(main())
