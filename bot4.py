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
    "WAGMI", "nice project", "Let's go", "Bullish", "looks great",
    "Excited!", "LFG", "lfg", "To the moon 🌙", "Great project 🔥",
    "Hey everyone", "hello there", "ser", "This is it", "Early gang 🤝",
    "Solid project", "solid project bro", "In it for the long run",
    "Diamond hands 💎", "diamond hands never sell 💎",
    "diamond hands only 💎🙌", "got my diamond hands ready",
    "Just joined!", "just joined the community",
    "Looks promising", "looks very promising ngl",
    "Let's build", "let's build together",
    "Happy to be here", "happy to be part of this"
]

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

async def get_latest_msg(app, bot):
    async for msg in app.get_chat_history(bot, limit=1):
        return msg
    return None

async def click_inline(msg, keywords):
    if not msg or not msg.reply_markup:
        return False
    if not hasattr(msg.reply_markup, 'inline_keyboard'):
        return False
    for row in msg.reply_markup.inline_keyboard:
        for btn in row:
            if any(k in btn.text.lower() for k in keywords):
                await msg.click(btn.text)
                return btn.text
    return False

async def click_reply(app, bot_username, msg, keywords):
    if not msg or not msg.reply_markup:
        return False
    if not hasattr(msg.reply_markup, 'keyboard'):
        return False
    for row in msg.reply_markup.keyboard:
        for btn in row:
            label = btn.text if hasattr(btn, 'text') else btn
            if any(k in label.lower() for k in keywords):
                await app.send_message(bot_username, label)
                return label
    return False

async def run_account(session_string, link_x, email, wallet, index, bot_username, start_param, do_chat):
    print(f"\n{'='*50}")
    print(f"[Akun {index}] Mulai → @{bot_username}")

    async with Client(
        name=f"acc_{index}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_string,
        in_memory=True
    ) as app:

        # STEP 1: /start
        start_cmd = f"/start {start_param}" if start_param else "/start"
        await app.send_message(bot_username, start_cmd)
        await asyncio.sleep(5)

        # STEP 2: Jawab captcha
        msg = await get_latest_msg(app, bot_username)
        text = msg.text or msg.caption or "" if msg else ""
        print(f"[Akun {index}] Pesan: {text[:80]}")

        answer = solve_captcha(text)
        if answer:
            await app.send_message(bot_username, answer)
            print(f"[Akun {index}] ✅ Jawab captcha: {answer}")
            await asyncio.sleep(4)
        else:
            print(f"[Akun {index}] ⚠️ Captcha tidak ditemukan")

        # STEP 3: Klik "Submit your details" (inline)
        msg = await get_latest_msg(app, bot_username)
        text = msg.text or msg.caption or "" if msg else ""
        print(f"[Akun {index}] Pesan: {text[:80]}")

        clicked = await click_inline(msg, ['submit', 'detail', 'start', 'begin'])
        if clicked:
            print(f"[Akun {index}] ✅ Klik inline: {clicked}")
        await asyncio.sleep(3)

        # STEP 4: Isi link X profile
        msg = await get_latest_msg(app, bot_username)
        text = msg.text or msg.caption or "" if msg else ""
        print(f"[Akun {index}] Pesan: {text[:80]}")

        await app.send_message(bot_username, link_x)
        print(f"[Akun {index}] ✅ Kirim link X: {link_x}")
        await asyncio.sleep(3)

        # STEP 5: Klik Done (reply keyboard)
        msg = await get_latest_msg(app, bot_username)
        text = msg.text or msg.caption or "" if msg else ""
        print(f"[Akun {index}] Pesan: {text[:80]}")

        clicked = await click_reply(app, bot_username, msg, ['done', 'selesai'])
        if clicked:
            print(f"[Akun {index}] ✅ Klik Done: {clicked}")
        await asyncio.sleep(3)

        # STEP 5.5: Join channel sebelum Yes
        msg = await get_latest_msg(app, bot_username)
        text = msg.text or msg.caption or "" if msg else ""
        print(f"[Akun {index}] Pesan join channel: {text[:120]}")

        tme_links = []
        if msg and msg.entities:
            for entity in msg.entities:
                url = None
                if entity.type.name == "TEXT_LINK": url = entity.url
                elif entity.type.name == "URL": url = (msg.text or "")[entity.offset:entity.offset+entity.length]
                if url and 't.me/' in url:
                    tme_links.append(url)
        if not tme_links:
            tme_links = re.findall(r'https?://t\.me/[\w+/]+', text)

        for link in tme_links:
            try:
                ch_username = link.replace("https://t.me/", "").replace("http://t.me/", "").replace("t.me/", "").strip("/")
                await app.join_chat(ch_username)
                print(f"[Akun {index}] ✅ Join channel: {ch_username}")
                break
            except Exception as e:
                if "already" in str(e).lower() or "USER_ALREADY" in str(e):
                    print(f"[Akun {index}] ✅ Sudah join channel")
                    break
                else:
                    print(f"[Akun {index}] ⚠️ Channel gagal, coba berikutnya: {e}")
            await asyncio.sleep(2)
        await asyncio.sleep(5)  # tunggu bot verify join

        # STEP 6: Klik Yes (reply keyboard)
        msg = await get_latest_msg(app, bot_username)
        text = msg.text or msg.caption or "" if msg else ""
        print(f"[Akun {index}] Pesan: {text[:80]}")

        clicked = await click_reply(app, bot_username, msg, ['yes', 'ya', 'iya'])
        if clicked:
            print(f"[Akun {index}] ✅ Klik Yes: {clicked}")
        await asyncio.sleep(3)

        # STEP 7: Isi email
        msg = await get_latest_msg(app, bot_username)
        text = msg.text or msg.caption or "" if msg else ""
        print(f"[Akun {index}] Pesan: {text[:80]}")

        await app.send_message(bot_username, email)
        print(f"[Akun {index}] ✅ Kirim email: {email}")
        await asyncio.sleep(3)

        # STEP 8: Isi wallet
        msg = await get_latest_msg(app, bot_username)
        text = msg.text or msg.caption or "" if msg else ""
        print(f"[Akun {index}] Pesan: {text[:80]}")

        await app.send_message(bot_username, wallet)
        print(f"[Akun {index}] ✅ Kirim wallet: {wallet}")
        await asyncio.sleep(3)

        # STEP 9: Klik Continue (reply keyboard)
        msg = await get_latest_msg(app, bot_username)
        text = msg.text or msg.caption or "" if msg else ""
        print(f"[Akun {index}] Pesan: {text[:80]}")

        clicked = await click_reply(app, bot_username, msg, ['continue', 'lanjut', 'next'])
        if clicked:
            print(f"[Akun {index}] ✅ Klik Continue: {clicked}")
        await asyncio.sleep(3)

        # STEP 10: Klik Complete the airdrop (reply keyboard)
        msg = await get_latest_msg(app, bot_username)
        text = msg.text or msg.caption or "" if msg else ""
        print(f"[Akun {index}] Pesan: {text[:80]}")

        clicked = await click_reply(app, bot_username, msg, ['complete', 'finish', 'claim', 'airdrop'])
        if clicked:
            print(f"[Akun {index}] ✅ Klik Complete: {clicked}")
        await asyncio.sleep(3)

        # Cek konfirmasi
        msg = await get_latest_msg(app, bot_username)
        text = msg.text or msg.caption or "" if msg else ""
        print(f"[Akun {index}] Pesan akhir: {text[:100]}")

        if any(k in text.lower() for k in ['success', 'berhasil', 'completed', 'thank', 'registered', 'reward', 'congratulation']):
            print(f"[Akun {index}] ✅ Quest selesai!")
        else:
            print(f"[Akun {index}] ⚠️ Cek manual")

# ── Menu ─────────────────────────────────────────────────
async def main():
    sessions = load_file("sessions.txt")
    data     = load_file("data4.txt")  # format: link_x|email|wallet

    if len(sessions) != len(data):
        print(f"⚠️ Jumlah sessions ({len(sessions)}) dan data ({len(data)}) tidak sama!")
        return

    total = len(sessions)

    print("\n╔══════════════════════════════╗")
    print("║       AIRDROP BOT 4          ║")
    print("╚══════════════════════════════╝")

    bot_link = input("\nMasukkan link bot: ").strip()
    bot_username, start_param = parse_bot_link(bot_link)
    if not bot_username:
        print("❌ Link tidak valid")
        return
    print(f"✅ Bot: @{bot_username} | Start: {start_param}")

    print(f"\n╔══════════════════════════════╗")
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
        link_x = parts[0].strip()
        email  = parts[1].strip()
        wallet = parts[2].strip()

        if chat_mode == "1":
            do_chat = True
        elif chat_mode == "2":
            do_chat = random.choice([True, False])
        else:
            do_chat = False

        await run_account(sessions[i], link_x, email, wallet, i + 1, bot_username, start_param, do_chat)
        if i != indices[-1]:
            print(f"\n⏳ Delay {DELAY_BETWEEN_ACCOUNTS} detik...")
            await asyncio.sleep(DELAY_BETWEEN_ACCOUNTS)

    print("\n✅ Semua akun selesai!")

if __name__ == "__main__":
    asyncio.run(main())
