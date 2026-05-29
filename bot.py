import asyncio
import re
from pyrogram import Client

# ── Config ──────────────────────────────────────────────
API_ID   = 0        # isi API ID lu
API_HASH = ""       # isi API Hash lu
DELAY_BETWEEN_ACCOUNTS = 10  # detik

# ── Load data ────────────────────────────────────────────
def load_file(path):
    with open(path, "r") as f:
        return [line.strip() for line in f if line.strip()]

def parse_bot_link(link):
    match = re.search(r't\.me/(\w+)\?start=(\w+)', link)
    if match:
        return match.group(1), match.group(2)
    match = re.search(r't\.me/(\w+)', link)
    if match:
        return match.group(1), None
    return None, None

def solve_captcha(text):
    match = re.search(r'[\(\[]?(\d+)\s*([+\-x*/×÷])\s*(\d+)[\)\]]?', text)
    if not match:
        return None
    a, op, b = int(match.group(1)), match.group(2), int(match.group(3))
    if op == '+': return str(a + b)
    elif op == '-': return str(a - b)
    elif op in ('x', '*', '×'): return str(a * b)
    elif op in ('/', '÷'): return str(a // b) if b != 0 else None
    return None

def extract_tme_from_entities(msg):
    if not msg.entities:
        return None
    for entity in msg.entities:
        url = None
        if entity.type.name == "TEXT_LINK":
            url = entity.url
        elif entity.type.name == "URL":
            url = (msg.text or "")[entity.offset:entity.offset+entity.length]
        if url and 't.me/' in url:
            return url
    return None

def extract_tme_link(text):
    match = re.search(r'https?://t\.me/[\w+/]+', text)
    if match:
        return match.group(0)
    match = re.search(r't\.me/([\w+/]+)', text)
    if match:
        return match.group(1)
    return None

async def get_latest_msg(app, bot):
    async for msg in app.get_chat_history(bot, limit=1):
        return msg
    return None

async def click_btn(msg, keywords):
    if not msg or not msg.reply_markup:
        return False
    for row in msg.reply_markup.inline_keyboard:
        for btn in row:
            if any(k in btn.text.lower() for k in keywords):
                await msg.click(btn.text)
                return btn.text
    return False

RANDOM_CHATS = [
    "hi", "Hello guys", "gm", "GM", "GM GM!", "gm gm",
    "WAGMI", "nice project", "Let's go",
    "Bullish", "looks great", "Excited!", "LFG", "lfg",
    "To the moon 🌙", "Great project 🔥", "Hey everyone",
    "hello there", "ser", "This is it", "Early gang 🤝",
    "Solid project", "solid project bro", "In it for the long run",
    "Diamond hands 💎", "diamond hands never sell 💎",
    "diamond hands only 💎🙌", "got my diamond hands ready",
    "Just joined!", "just joined the community",
    "Looks promising", "looks very promising ngl",
    "Let's build", "let's build together",
    "Happy to be here", "happy to be part of this"
]

async def send_random_chat(app, group_username, index):
    import random
    msg = random.choice(RANDOM_CHATS)
    try:
        print(f"[Akun {index}] Kirim ke group: {group_username}")
        await app.send_message(group_username, msg)
        print(f"[Akun {index}] ✅ Random chat: {msg}")
    except Exception as e:
        print(f"[Akun {index}] ⚠️ Random chat gagal: {e}")

async def handle_group_captcha(app, group_username, my_username, index):
    """Monitor group 10 detik, jawab captcha kalau ada mention @username akun ini"""
    print(f"[Akun {index}] Monitor captcha group selama 10 detik...")
    for _ in range(10):
        await asyncio.sleep(1)
        try:
            async for msg in app.get_chat_history(group_username, limit=5):
                text = msg.text or ""
                if f"@{my_username}".lower() in text.lower():
                    answer = solve_captcha(text)
                    if answer:
                        await app.send_message(group_username, answer)
                        print(f"[Akun {index}] ✅ Jawab captcha group: {answer}")
                        return
        except Exception as e:
            print(f"[Akun {index}] ⚠️ Monitor group error: {e}")
            return
    print(f"[Akun {index}] Tidak ada captcha group, lanjut...")

# ── Core logic per akun ──────────────────────────────────
async def run_account(session_string, twitter_username, wallet_address, index, bot_username, start_param):
    print(f"\n{'='*50}")
    print(f"[Akun {index}] Mulai → @{bot_username}")

    async with Client(
        name=f"acc_{index}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_string,
        in_memory=True
    ) as app:

        # Ambil username akun ini
        me = await app.get_me()
        my_username = me.username or str(me.id)
        print(f"[Akun {index}] Username: @{my_username}")

        # STEP 1: /start
        start_cmd = f"/start {start_param}" if start_param else "/start"
        await app.send_message(bot_username, start_cmd)
        await asyncio.sleep(5)

        # STEP 2: Baca pesan captcha
        msg = await get_latest_msg(app, bot_username)
        if not msg:
            print(f"[Akun {index}] ❌ Tidak ada pesan dari bot")
            return

        text = msg.text or msg.caption or ""
        print(f"[Akun {index}] Pesan: {text[:80]}")

        answer = solve_captcha(text)
        if not answer:
            print(f"[Akun {index}] ❌ Soal captcha tidak ditemukan")
            return
        print(f"[Akun {index}] Jawaban captcha: {answer}")

        # STEP 3: Klik Continue
        clicked = await click_btn(msg, ['continue'])
        if not clicked:
            print(f"[Akun {index}] ❌ Tombol Continue tidak ditemukan")
            return
        print(f"[Akun {index}] ✅ Klik: {clicked}")
        await asyncio.sleep(4)

        # STEP 4: Kirim jawaban captcha
        await app.send_message(bot_username, answer)
        print(f"[Akun {index}] ✅ Kirim jawaban: {answer}")
        await asyncio.sleep(4)

        # STEP 5: Baca pesan link group + tombol Done
        msg = await get_latest_msg(app, bot_username)
        text = msg.text or msg.caption or "" if msg else ""
        print(f"[Akun {index}] Pesan: {text[:120]}")

        # Extract & join group
        link = extract_tme_from_entities(msg) or extract_tme_link(text)
        print(f"[Akun {index}] Link extracted: {link}")
        group_username = None
        if link:
            try:
                group_username = link.replace("https://t.me/", "").replace("http://t.me/", "").replace("t.me/", "").strip("/")
                await app.join_chat(group_username)
                print(f"[Akun {index}] ✅ Join group: {group_username}")
                await asyncio.sleep(2)
                # Handle captcha group dulu
                await handle_group_captcha(app, group_username, my_username, index)
                # Baru random chat
                await send_random_chat(app, group_username, index)
            except Exception as e:
                print(f"[Akun {index}] ⚠️ Join group gagal: {e}")
        else:
            print(f"[Akun {index}] ⚠️ Link group tidak ditemukan")
        await asyncio.sleep(3)

        # STEP 6: Klik Done (setelah join group)
        msg = await get_latest_msg(app, bot_username)
        clicked = await click_btn(msg, ['done', 'selesai'])
        if clicked:
            print(f"[Akun {index}] ✅ Klik: {clicked}")
        await asyncio.sleep(4)

        # STEP 7: Kirim username X
        msg = await get_latest_msg(app, bot_username)
        text = msg.text or msg.caption or "" if msg else ""
        print(f"[Akun {index}] Pesan: {text[:80]}")

        await app.send_message(bot_username, twitter_username)
        print(f"[Akun {index}] ✅ Kirim Twitter: {twitter_username}")
        await asyncio.sleep(4)

        # STEP 8: Popup Discord → klik Done (kalau ada)
        msg = await get_latest_msg(app, bot_username)
        text = msg.text or msg.caption or "" if msg else ""
        print(f"[Akun {index}] Pesan: {text[:80]}")

        if any(k in text.lower() for k in ['discord']):
            clicked = await click_btn(msg, ['done', 'skip', 'selesai'])
            if clicked:
                print(f"[Akun {index}] ✅ Klik Done (discord): {clicked}")
            await asyncio.sleep(4)
            msg = await get_latest_msg(app, bot_username)
            text = msg.text or msg.caption or "" if msg else ""
            print(f"[Akun {index}] Pesan: {text[:80]}")

        # STEP 9: Popup advertiser → klik Done
        clicked = await click_btn(msg, ['done', 'skip', 'selesai'])
        if clicked:
            print(f"[Akun {index}] ✅ Klik Done (advertiser): {clicked}")
        await asyncio.sleep(4)

        # STEP 10: Submit wallet
        msg = await get_latest_msg(app, bot_username)
        text = msg.text or msg.caption or "" if msg else ""
        print(f"[Akun {index}] Pesan: {text[:80]}")

        await app.send_message(bot_username, wallet_address)
        print(f"[Akun {index}] ✅ Kirim wallet: {wallet_address}")
        await asyncio.sleep(4)

        # Cek konfirmasi akhir
        msg = await get_latest_msg(app, bot_username)
        text = msg.text or msg.caption or "" if msg else ""
        print(f"[Akun {index}] Pesan akhir: {text[:100]}")

        if any(k in text.lower() for k in ['success', 'berhasil', 'completed', 'reward', 'congratulation', 'thank', 'registered']):
            print(f"[Akun {index}] ✅ Quest selesai!")
        else:
            print(f"[Akun {index}] ⚠️ Cek manual, mungkin ada step tambahan")

# ── Menu ─────────────────────────────────────────────────
def print_menu(total):
    print("\n╔══════════════════════════════╗")
    print("║         AIRDROP BOT          ║")
    print("╠══════════════════════════════╣")
    print(f"║  Total akun: {total:<17}║")
    print("╠══════════════════════════════╣")
    print("║  1. Jalanin semua akun       ║")
    print("║  2. Pilih satu akun          ║")
    print("║  3. From akun ke-N           ║")
    print("╚══════════════════════════════╝")

async def main():
    sessions = load_file("sessions.txt")
    data     = load_file("data.txt")

    if len(sessions) != len(data):
        print(f"⚠️  Jumlah sessions ({len(sessions)}) dan data ({len(data)}) tidak sama!")
        return

    total = len(sessions)

    print("\n╔══════════════════════════════╗")
    print("║         AIRDROP BOT          ║")
    print("╚══════════════════════════════╝")
    bot_link = input("Masukkan link bot: ").strip()
    bot_username, start_param = parse_bot_link(bot_link)

    if not bot_username:
        print("❌ Link tidak valid")
        return

    print(f"✅ Bot: @{bot_username} | Start param: {start_param}")

    print_menu(total)
    choice = input("\nPilih mode (1/2/3): ").strip()

    if choice == "1":
        indices = list(range(total))
    elif choice == "2":
        idx = int(input(f"Pilih akun (1-{total}): ")) - 1
        indices = [idx]
    elif choice == "3":
        start = int(input(f"Mulai dari akun ke- (1-{total}): ")) - 1
        indices = list(range(start, total))
    else:
        print("Pilihan tidak valid.")
        return

    print(f"\n▶ Menjalankan {len(indices)} akun...\n")

    for i in indices:
        twitter, wallet = data[i].split("|")
        await run_account(sessions[i], twitter.strip(), wallet.strip(), i + 1, bot_username, start_param)
        if i != indices[-1]:
            print(f"\n⏳ Delay {DELAY_BETWEEN_ACCOUNTS} detik sebelum akun berikutnya...")
            await asyncio.sleep(DELAY_BETWEEN_ACCOUNTS)

    print("\n✅ Semua akun selesai diproses!")

if __name__ == "__main__":
    asyncio.run(main())
