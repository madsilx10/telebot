import asyncio
import re
from pyrogram import Client

# ── Config ──────────────────────────────────────────────
API_ID   = 0        # isi API ID lu
API_HASH = ""       # isi API Hash lu
BOT_USERNAME = "EXEGroupCEXListingAirdropBot"
START_PARAM  = "2005545171"
DELAY_BETWEEN_ACCOUNTS = 10  # detik

# ── Load data ────────────────────────────────────────────
def load_file(path):
    with open(path, "r") as f:
        return [line.strip() for line in f if line.strip()]

def solve_captcha(text):
    match = re.search(r'(\d+)\s*([+\-x*/×÷])\s*(\d+)', text)
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

async def wait_for_reply(app, bot, timeout=15):
    """Tunggu pesan baru dari bot, max timeout detik"""
    for _ in range(timeout):
        await asyncio.sleep(1)
        msg = await get_latest_msg(app, bot)
        if msg:
            return msg
    return None

# ── Core logic per akun ──────────────────────────────────
async def run_account(session_string, twitter_username, wallet_address, index):
    print(f"\n{'='*50}")
    print(f"[Akun {index}] Mulai...")

    async with Client(
        name=f"acc_{index}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_string,
        in_memory=True
    ) as app:

        # STEP 1: /start dengan referral
        await app.send_message(BOT_USERNAME, f"/start {START_PARAM}")
        await asyncio.sleep(5)

        # STEP 2: Ambil pesan terbaru — harusnya ada soal captcha + tombol Continue
        msg = await get_latest_msg(app, BOT_USERNAME)
        if not msg:
            print(f"[Akun {index}] ❌ Tidak ada pesan dari bot")
            return

        text = msg.text or msg.caption or ""
        print(f"[Akun {index}] Pesan: {text[:80]}")

        # Cari soal captcha
        answer = solve_captcha(text)
        if not answer:
            print(f"[Akun {index}] ❌ Tidak ketemu soal captcha di pesan")
            return
        print(f"[Akun {index}] Soal: {text.strip()[:60]} → Jawaban: {answer}")

        # STEP 3: Klik tombol Continue
        clicked = False
        if msg.reply_markup:
            for row in msg.reply_markup.inline_keyboard:
                for btn in row:
                    if 'continue' in btn.text.lower():
                        await msg.click(btn.text)
                        print(f"[Akun {index}] Klik: {btn.text}")
                        clicked = True
                        break
        if not clicked:
            print(f"[Akun {index}] ⚠️ Tombol Continue tidak ditemukan")
            return

        # Tunggu bot balas "Great, please enter the code"
        await asyncio.sleep(4)

        # STEP 4: Kirim jawaban captcha
        await app.send_message(BOT_USERNAME, answer)
        print(f"[Akun {index}] Kirim jawaban: {answer}")
        await asyncio.sleep(4)

        # STEP 5: Cek pesan berikutnya — harusnya ada tombol Join Group
        msg = await get_latest_msg(app, BOT_USERNAME)
        text = msg.text or msg.caption or "" if msg else ""
        print(f"[Akun {index}] Pesan: {text[:80]}")

        # Klik Join Group
        joined = False
        if msg and msg.reply_markup:
            for row in msg.reply_markup.inline_keyboard:
                for btn in row:
                    if 'join' in btn.text.lower():
                        await msg.click(btn.text)
                        print(f"[Akun {index}] Klik: {btn.text}")
                        joined = True
                        await asyncio.sleep(5)
                        break

        if not joined:
            print(f"[Akun {index}] ⚠️ Tombol Join tidak ditemukan, lanjut...")

        # STEP 6: Klik Done
        msg = await get_latest_msg(app, BOT_USERNAME)
        if msg and msg.reply_markup:
            for row in msg.reply_markup.inline_keyboard:
                for btn in row:
                    if any(k in btn.text.lower() for k in ['done', 'verify', 'check']):
                        await msg.click(btn.text)
                        print(f"[Akun {index}] Klik: {btn.text}")
                        await asyncio.sleep(4)
                        break

        # STEP 7: Kirim username Twitter/X
        msg = await get_latest_msg(app, BOT_USERNAME)
        text = msg.text or msg.caption or "" if msg else ""
        print(f"[Akun {index}] Pesan: {text[:80]}")

        if any(k in text.lower() for k in ['twitter', 'x.com', 'username', 'follow']):
            await app.send_message(BOT_USERNAME, twitter_username)
            print(f"[Akun {index}] Kirim Twitter: {twitter_username}")
            await asyncio.sleep(4)

        # STEP 7b: Klik Continue kalau ada (optional)
        msg = await get_latest_msg(app, BOT_USERNAME)
        if msg and msg.reply_markup:
            for row in msg.reply_markup.inline_keyboard:
                for btn in row:
                    if 'continue' in btn.text.lower():
                        await msg.click(btn.text)
                        print(f"[Akun {index}] Klik Continue (post-twitter): {btn.text}")
                        await asyncio.sleep(3)
                        break

        # STEP 8: Kirim wallet address
        msg = await get_latest_msg(app, BOT_USERNAME)
        text = msg.text or msg.caption or "" if msg else ""
        print(f"[Akun {index}] Pesan: {text[:80]}")

        if any(k in text.lower() for k in ['wallet', 'address', 'bsc', 'evm', '0x', 'submit']):
            await app.send_message(BOT_USERNAME, wallet_address)
            print(f"[Akun {index}] Kirim Wallet: {wallet_address}")
            await asyncio.sleep(4)

        # Cek konfirmasi selesai
        msg = await get_latest_msg(app, BOT_USERNAME)
        text = msg.text or msg.caption or "" if msg else ""
        print(f"[Akun {index}] Pesan akhir: {text[:80]}")

        if any(k in text.lower() for k in ['success', 'berhasil', 'completed', 'reward', 'congratulation', 'thank']):
            print(f"[Akun {index}] ✅ Quest selesai!")
        else:
            print(f"[Akun {index}] ⚠️ Selesai tapi belum konfirmasi sukses, cek manual")

# ── Menu ─────────────────────────────────────────────────
def print_menu(total):
    print("\n╔══════════════════════════════╗")
    print("║     PEGABANK QUEST BOT       ║")
    print("╠══════════════════════════════╣")
    print(f"║  Total akun: {total:<17}║")
    print("╠══════════════════════════════╣")
    print("║  1. Jalanin semua akun       ║")
    print("║  2. Pilih satu akun          ║")
    print("║  3. From akun ke-N           ║")
    print("╚══════════════════════════════╝")

async def main():
    sessions = load_file("sessions.txt")
    data     = load_file("data.txt")  # format: username_x|wallet_address

    if len(sessions) != len(data):
        print(f"⚠️  Jumlah sessions ({len(sessions)}) dan data ({len(data)}) tidak sama!")
        return

    total = len(sessions)
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
        await run_account(sessions[i], twitter.strip(), wallet.strip(), i + 1)
        if i != indices[-1]:
            print(f"\n⏳ Delay {DELAY_BETWEEN_ACCOUNTS} detik sebelum akun berikutnya...")
            await asyncio.sleep(DELAY_BETWEEN_ACCOUNTS)

    print("\n✅ Semua akun selesai diproses!")

if __name__ == "__main__":
    asyncio.run(main())
