import asyncio
import re
import random
from pyrogram import Client

# ── Config ──────────────────────────────────────────────
API_ID   = 0        # isi API ID lu
API_HASH = ""       # isi API Hash lu
DELAY_BETWEEN_ACCOUNTS = 10

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

SUBMIT_KEYWORDS = [
    "submit", "detail", "register", "fill", "enter",
    "participate", "claim", "daftar", "input", "join airdrop"
]

# ── Helpers ──────────────────────────────────────────────
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

def generate_rt_link(twitter_username):
    random_id = random.randint(2000000000000000000, 2099999999999999999)
    return f"https://x.com/{twitter_username}/status/{random_id}"

async def get_latest_msg(app, bot):
    async for msg in app.get_chat_history(bot, limit=1):
        return msg
    return None

async def click_btn(msg, index, label=""):
    """Klik button berdasarkan SUBMIT_KEYWORDS, fallback ke button pertama."""
    if not msg or not msg.reply_markup:
        return None
    all_btns = [btn for row in msg.reply_markup.inline_keyboard for btn in row]
    if not all_btns:
        return None

    print(f"[Akun {index}] {label} Buttons: {[b.text for b in all_btns]}")

    for kw in SUBMIT_KEYWORDS:
        for btn in all_btns:
            if kw in btn.text.lower():
                try:
                    await msg.click(btn.text)
                    print(f"[Akun {index}] ✅ Klik: '{btn.text}'")
                    return btn.text
                except Exception as e:
                    print(f"[Akun {index}] ⚠️ Gagal klik '{btn.text}': {e}")

    # Fallback klik pertama
    try:
        await msg.click(all_btns[0].text)
        print(f"[Akun {index}] ✅ Klik fallback: '{all_btns[0].text}'")
        return all_btns[0].text
    except Exception as e:
        print(f"[Akun {index}] ⚠️ Gagal klik fallback: {e}")
        return None

async def handle_group_captcha(app, group_username, my_username, index):
    print(f"[Akun {index}] Monitor captcha group 10 detik...")
    for _ in range(10):
        await asyncio.sleep(1)
        try:
            async for msg in app.get_chat_history(group_username, limit=5):
                text = msg.text or ""
                if f"@{my_username}".lower() in text.lower():
                    match = re.search(r'[\(\[]?(\d+)\s*([+\-x*/×÷])\s*(\d+)[\)\]]?', text)
                    if match:
                        a, op, b = int(match.group(1)), match.group(2), int(match.group(3))
                        if op == '+': ans = str(a + b)
                        elif op == '-': ans = str(a - b)
                        elif op in ('x', '*', '×'): ans = str(a * b)
                        else: ans = str(a // b)
                        await app.send_message(group_username, ans)
                        print(f"[Akun {index}] ✅ Jawab captcha: {ans}")
                        return
        except Exception as e:
            print(f"[Akun {index}] ⚠️ Monitor error: {e}")
            return
    print(f"[Akun {index}] Tidak ada captcha, lanjut...")

# ── Core logic per akun ──────────────────────────────────
async def run_account(session_string, twitter_username, wallet_address, email, index, bot_username, start_param, do_chat):
    print(f"\n{'='*50}")
    print(f"[Akun {index}] Mulai → @{bot_username}")

    async with Client(
        name=f"acc_{index}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_string,
        in_memory=True
    ) as app:
        me = await app.get_me()
        my_username = me.username or str(me.id)

        # STEP 1: /start
        start_cmd = f"/start {start_param}" if start_param else "/start"
        await app.send_message(bot_username, start_cmd)
        await asyncio.sleep(5)

        # STEP 2: Baca pesan — join group
        msg = await get_latest_msg(app, bot_username)
        text = msg.text or msg.caption or "" if msg else ""
        print(f"[Akun {index}] Pesan: {text[:100]}")

        link = extract_tme_from_entities(msg) or extract_tme_link(text)
        print(f"[Akun {index}] Link group: {link}")
        group_username = None
        if link:
            try:
                group_username = link.replace("https://t.me/", "").replace("http://t.me/", "").replace("t.me/", "").strip("/")
                await app.join_chat(group_username)
                print(f"[Akun {index}] ✅ Join: {group_username}")
                await asyncio.sleep(2)
                await handle_group_captcha(app, group_username, my_username, index)
                await asyncio.sleep(3)
                if do_chat:
                    chat_msg = random.choice(RANDOM_CHATS)
                    await app.send_message(group_username, chat_msg)
                    print(f"[Akun {index}] ✅ Chat: {chat_msg}")
            except Exception as e:
                print(f"[Akun {index}] ⚠️ Join gagal: {e}")
        await asyncio.sleep(3)

        # STEP 2.5: Klik "Submit Details" / sejenisnya
        msg = await get_latest_msg(app, bot_username)
        clicked = await click_btn(msg, index, "[Submit Details]")
        if clicked:
            await asyncio.sleep(4)
        else:
            print(f"[Akun {index}] ⚠️ Tidak ada button Submit Details")
        await asyncio.sleep(2)

        # ── Helper kirim data ──
        async def send_data(value, label):
            msg = await get_latest_msg(app, bot_username)
            text = msg.text or msg.caption or "" if msg else ""
            print(f"[Akun {index}] Pesan: {text[:80]}")
            await app.send_message(bot_username, value)
            print(f"[Akun {index}] ✅ Kirim {label}: {value}")
            await asyncio.sleep(3)

        # STEP 3: Kirim username Telegram
        await send_data(f"@{my_username}", "usn Tele")

        # STEP 4: Kirim username X
        await send_data(twitter_username, "Twitter")

        # STEP 5: Kirim email
        await send_data(email, "Email")

        # STEP 6: Kirim RT link
        rt_link = generate_rt_link(twitter_username.lstrip('@'))
        await send_data(rt_link, "RT link")

        # STEP 7: Kirim wallet
        await send_data(wallet_address, "Wallet")

        # Cek konfirmasi akhir
        await asyncio.sleep(2)
        msg = await get_latest_msg(app, bot_username)
        text = msg.text or msg.caption or "" if msg else ""
        print(f"[Akun {index}] Pesan akhir: {text[:100]}")

        if any(k in text.lower() for k in ['success', 'berhasil', 'completed', 'thank', 'registered', 'reward']):
            print(f"[Akun {index}] ✅ Quest selesai!")
        else:
            print(f"[Akun {index}] ⚠️ Cek manual")

# ── Menu ─────────────────────────────────────────────────
async def main():
    sessions = load_file("sessions.txt")
    data     = load_file("data.txt")  # format: username_x|wallet|email

    if len(sessions) != len(data):
        print(f"⚠️ Jumlah sessions ({len(sessions)}) dan data ({len(data)}) tidak sama!")
        return

    total = len(sessions)

    print("\n╔══════════════════════════════╗")
    print("║       AIRDROP BOT 2          ║")
    print("╚══════════════════════════════╝")

    bot_link = input("\nMasukkan link bot: ").strip()
    bot_username, start_param = parse_bot_link(bot_link)
    if not bot_username:
        print("❌ Link tidak valid")
        return
    print(f"✅ Bot: @{bot_username} | Start: {start_param}")

    print("\n╔══════════════════════════════╗")
    print(f"║  Total akun: {total:<17}║")
    print("╠══════════════════════════════╣")
    print("║  1. Jalanin semua akun       ║")
    print("║  2. Pilih satu akun          ║")
    print("║  3. From akun ke-N           ║")
    print("╚══════════════════════════════╝")
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

    print("\n╔══════════════════════════════╗")
    print("║      MODE RANDOM CHAT        ║")
    print("╠══════════════════════════════╣")
    print("║  1. Semua akun kirim chat    ║")
    print("║  2. Random akun kirim chat   ║")
    print("║  3. Tidak kirim chat         ║")
    print("╚══════════════════════════════╝")
    chat_mode = input("\nPilih mode chat (1/2/3): ").strip()

    print(f"\n▶ Menjalankan {len(indices)} akun...\n")

    for i in indices:
        parts = data[i].split("|")
        twitter = parts[0].strip()
        wallet  = parts[1].strip()
        email   = parts[2].strip() if len(parts) > 2 else ""

        if chat_mode == "1":
            do_chat = True
        elif chat_mode == "2":
            do_chat = random.choice([True, False])
        else:
            do_chat = False

        await run_account(sessions[i], twitter, wallet, email, i + 1, bot_username, start_param, do_chat)
        if i != indices[-1]:
            print(f"\n⏳ Delay {DELAY_BETWEEN_ACCOUNTS} detik...")
            await asyncio.sleep(DELAY_BETWEEN_ACCOUNTS)

    print("\n✅ Semua akun selesai!")

if __name__ == "__main__":
    asyncio.run(main())
