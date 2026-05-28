import asyncio
import re
from pyrogram import Client
from pyrogram.types import Message

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
    """Cari soal matematika di teks dan jawab otomatis"""
    match = re.search(r'(\d+)\s*([+\-x*/×÷])\s*(\d+)', text)
    if not match:
        return None
    a, op, b = int(match.group(1)), match.group(2), int(match.group(3))
    if op in ('+'):
        return str(a + b)
    elif op in ('-'):
        return str(a - b)
    elif op in ('x', '*', '×'):
        return str(a * b)
    elif op in ('/', '÷'):
        return str(a // b) if b != 0 else None
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

        # Start bot dengan referral
        await app.send_message(BOT_USERNAME, f"/start {START_PARAM}")
        await asyncio.sleep(3)

        async for msg in app.get_chat_history(BOT_USERNAME, limit=5):
            # Klik tombol Continue / Start
            if msg.reply_markup:
                for row in msg.reply_markup.inline_keyboard:
                    for btn in row:
                        label = btn.text.lower()
                        if any(k in label for k in ['continue', 'start', 'mulai', 'lanjut']):
                            await msg.click(btn.text)
                            print(f"[Akun {index}] Klik: {btn.text}")
                            await asyncio.sleep(3)
                            break
            break

        # Loop baca pesan & handle tiap step
        done_steps = set()
        max_attempts = 20

        for attempt in range(max_attempts):
            await asyncio.sleep(2)

            async for msg in app.get_chat_history(BOT_USERNAME, limit=3):
                text = msg.text or msg.caption or ""

                # ── Captcha ──
                if "captcha" in text.lower() or re.search(r'\d+\s*[+\-x*/×÷]\s*\d+', text):
                    if "captcha" not in done_steps:
                        answer = solve_captcha(text)
                        if answer:
                            await app.send_message(BOT_USERNAME, answer)
                            print(f"[Akun {index}] Captcha: {text.strip()[:50]} → {answer}")
                            done_steps.add("captcha")
                            await asyncio.sleep(2)

                # ── Tombol inline ──
                if msg.reply_markup:
                    for row in msg.reply_markup.inline_keyboard:
                        for btn in row:
                            label = btn.text.lower()

                            # Join group
                            if 'join' in label and 'join' not in done_steps:
                                await msg.click(btn.text)
                                print(f"[Akun {index}] Klik Join: {btn.text}")
                                done_steps.add("join")
                                await asyncio.sleep(3)

                            # Done / Verify
                            elif any(k in label for k in ['done', 'verify', 'check', 'selesai']) and 'done' not in done_steps:
                                await msg.click(btn.text)
                                print(f"[Akun {index}] Klik Done: {btn.text}")
                                done_steps.add("done")
                                await asyncio.sleep(3)

                            # Continue setelah username
                            elif any(k in label for k in ['continue', 'lanjut', 'next']) and 'twitter' in done_steps and 'continue2' not in done_steps:
                                await msg.click(btn.text)
                                print(f"[Akun {index}] Klik Continue (post-twitter): {btn.text}")
                                done_steps.add("continue2")
                                await asyncio.sleep(2)

                # ── Minta Twitter ──
                if any(k in text.lower() for k in ['twitter', 'username', '@', 'x.com']) and 'twitter' not in done_steps:
                    await app.send_message(BOT_USERNAME, twitter_username)
                    print(f"[Akun {index}] Kirim Twitter: {twitter_username}")
                    done_steps.add("twitter")
                    await asyncio.sleep(2)

                # ── Minta Wallet ──
                if any(k in text.lower() for k in ['wallet', 'address', 'bsc', 'evm', '0x']) and 'wallet' not in done_steps and 'twitter' in done_steps:
                    await app.send_message(BOT_USERNAME, wallet_address)
                    print(f"[Akun {index}] Kirim Wallet: {wallet_address}")
                    done_steps.add("wallet")
                    await asyncio.sleep(2)

                # ── Selesai ──
                if any(k in text.lower() for k in ['success', 'berhasil', 'completed', 'reward', 'congratulation']):
                    print(f"[Akun {index}] ✅ Quest selesai!")
                    return

                break  # cukup cek pesan terbaru

            # Kalau semua step done, keluar
            if {'captcha', 'join', 'done', 'twitter', 'wallet'}.issubset(done_steps):
                print(f"[Akun {index}] ✅ Semua step selesai!")
                return

        print(f"[Akun {index}] ⚠️ Max attempt tercapai, lanjut ke akun berikutnya")

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
