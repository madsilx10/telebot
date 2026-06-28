import asyncio
import re
import os
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.errors import FloodWait, UserAlreadyParticipant, InviteHashExpired

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BOT_USERNAME = "GemXAppBot"        # bot target
START_PARAM  = "2005545171"        # parameter referral /start
SESSION_DIR  = "sessions"
SESSION_FILE = "sessions.txt"
CHANNEL_FILE = "channels.txt"
API_ID       = 0                  # isi API_ID lo
API_HASH     = ""                 # isi API_HASH lo
DELAY        = 3                  # delay antar aksi (detik)
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
        for line in f:
            name = line.strip()
            if name:
                sessions.append(name)
    return sessions

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
    """Parse dan solve captcha matematika sederhana dari teks pesan."""
    # cari pola: angka operator angka, contoh: 12 * 3, 5 + 7, 20 - 4, 18 / 3
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

async def join_channels(client: Client, channels: list, session_name: str):
    for ch in channels:
        try:
            await client.join_chat(ch)
            print(f"  [+] Joined: {ch}")
        except UserAlreadyParticipant:
            print(f"  [=] Already joined: {ch}")
        except InviteHashExpired:
            print(f"  [!] Link expired: {ch}")
        except FloodWait as e:
            print(f"  [~] FloodWait {e.value}s saat join {ch}, nunggu...")
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"  [!] Gagal join {ch}: {e}")
        await asyncio.sleep(DELAY)

async def click_button(client: Client, msg: Message, keyword: str):
    """Klik inline button yang mengandung keyword (case-insensitive)."""
    if not msg.reply_markup:
        return False
    for row in msg.reply_markup.inline_keyboard:
        for btn in row:
            if keyword.lower() in btn.text.lower():
                await msg.click(btn.text)
                print(f"  [+] Klik tombol: {btn.text}")
                return True
    return False

async def run_account(session_name: str, channels: list):
    session_path = os.path.join(SESSION_DIR, session_name)
    print(f"\n[*] Akun: {session_name}")

    async with Client(session_path, api_id=API_ID, api_hash=API_HASH) as app:
        me = await app.get_me()
        print(f"  [+] Login: {me.first_name} (@{me.username})")

        # 1. Join channels dulu
        if channels:
            print(f"  [*] Join {len(channels)} channel...")
            await join_channels(app, channels, session_name)

        # 2. Kirim /start ke bot
        print(f"  [*] /start ke @{BOT_USERNAME} (ref: {START_PARAM})")
        try:
            await app.send_message(BOT_USERNAME, f"/start {START_PARAM}")
        except FloodWait as e:
            print(f"  [~] FloodWait {e.value}s, nunggu...")
            await asyncio.sleep(e.value)
            await app.send_message(BOT_USERNAME, f"/start {START_PARAM}")

        await asyncio.sleep(DELAY)

        # 3. Ambil pesan terakhir dari bot
        msgs = []
        async for m in app.get_chat_history(BOT_USERNAME, limit=5):
            msgs.append(m)

        captcha_solved = False
        for msg in msgs:
            if msg.from_user and msg.from_user.username and \
               msg.from_user.username.lower() == BOT_USERNAME.lower():
                text = msg.text or msg.caption or ""

                # 4. Cek captcha matematika
                answer = solve_captcha(text)
                if answer and not captcha_solved:
                    print(f"  [*] Captcha ditemukan, jawaban: {answer}")
                    await app.send_message(BOT_USERNAME, answer)
                    captcha_solved = True
                    await asyncio.sleep(DELAY)

                    # Refresh pesan setelah jawab captcha
                    async for new_msg in app.get_chat_history(BOT_USERNAME, limit=3):
                        msgs.insert(0, new_msg)
                    break

        # 5. Klik tombol Check
        await asyncio.sleep(DELAY)
        async for msg in app.get_chat_history(BOT_USERNAME, limit=5):
            if msg.reply_markup:
                clicked = await click_button(app, msg, "check")
                if clicked:
                    await asyncio.sleep(DELAY)
                    break

        # 6. Klik tombol GemX Box
        await asyncio.sleep(DELAY)
        async for msg in app.get_chat_history(BOT_USERNAME, limit=5):
            if msg.reply_markup:
                clicked = await click_button(app, msg, "gemx box")
                if not clicked:
                    clicked = await click_button(app, msg, "box")
                if clicked:
                    await asyncio.sleep(DELAY)
                    break

        print(f"  [+] Selesai: {session_name}")

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
        for i, s in enumerate(sessions, 1):
            print(f"  {i}. {s}")
        idx = int(input("Pilih nomor akun: ").strip()) - 1
        target = [sessions[idx]]

    elif choice == "2":
        target = sessions

    elif choice == "3":
        print("\nDaftar akun:")
        for i, s in enumerate(sessions, 1):
            print(f"  {i}. {s}")
        start = int(input("Dari nomor akun: ").strip()) - 1
        target = sessions[start:]

    else:
        print("[!] Pilihan tidak valid")
        return

    print(f"\n[*] Menjalankan {len(target)} akun...\n")
    for session_name in target:
        try:
            await run_account(session_name, channels)
        except Exception as e:
            print(f"  [!] Error pada {session_name}: {e}")
        await asyncio.sleep(2)

    print("\n[+] Semua akun selesai diproses.")

if __name__ == "__main__":
    asyncio.run(main())
