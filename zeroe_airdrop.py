"""
ZeroE Airdrop Bot Automation - Multi Account
Bot target: @ZeroEDEXAirdropBot

Files needed (taruh di folder yang sama):
  - sessions.txt  -> 1 pyrogram session string per baris
  - data.txt      -> format per baris: username_x|wallet|email

Install dulu:
  pip install pyrogram tgcrypto --break-system-packages

Isi API_ID / API_HASH di bawah (punya lu sendiri dari my.telegram.org,
dipakai bareng semua session string).
"""

import asyncio
import random
import re
import logging
from pyrogram import Client
from pyrogram.errors import FloodWait

# ==================== CONFIG ====================
API_ID = 12345678          # ganti sesuai punya lu
API_HASH = "your_api_hash_here"  # ganti sesuai punya lu

BOT_USERNAME = "ZeroEDEXAirdropBot"
START_PARAM = "ref_2005545171"

SESSIONS_FILE = "sessions.txt"
XPROFILE_FILE = "x_profile.txt"
WALLET_FILE = "wallet.txt"
EMAIL_FILE = "email.txt"

DELAY_BETWEEN_STEPS = (2, 5)     # detik, random delay tiap step
DELAY_BETWEEN_ACCOUNTS = (10, 25)  # detik, random delay antar akun
WAIT_FOR_REPLY_TIMEOUT = 15      # detik, nunggu bot balas

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("zeroe")


# ==================== HELPERS ====================
def load_sessions(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def load_lines(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def load_data(xprofile_path, wallet_path, email_path):
    usernames = load_lines(xprofile_path)
    wallets = load_lines(wallet_path)
    emails = load_lines(email_path)

    n = min(len(usernames), len(wallets), len(emails))
    if not (len(usernames) == len(wallets) == len(emails)):
        log.warning(
            f"Jumlah baris beda! x_profile={len(usernames)}, wallet={len(wallets)}, "
            f"email={len(emails)}. Dipangkas ke {n} baris."
        )

    rows = []
    for i in range(n):
        rows.append({"username": usernames[i], "wallet": wallets[i], "email": emails[i]})
    return rows


def solve_math(text):
    """Cari ekspresi matematika simple di teks captcha, misal '5 + 3 = ?'."""
    match = re.search(r"(\d+)\s*([\+\-\*x×])\s*(\d+)", text)
    if not match:
        return None
    a, op, b = match.groups()
    a, b = int(a), int(b)
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op in ("*", "x", "×"):
        return a * b
    return None


async def rand_delay(rng):
    await asyncio.sleep(random.uniform(*rng))


def find_button(message, *keywords):
    """Cari inline/reply keyboard button yang teksnya mengandung salah satu keyword."""
    keywords = [k.lower() for k in keywords]

    if message.reply_markup:
        # Inline keyboard
        if hasattr(message.reply_markup, "inline_keyboard"):
            for row in message.reply_markup.inline_keyboard:
                for btn in row:
                    if any(k in btn.text.lower() for k in keywords):
                        return btn.text, "inline"
        # Reply keyboard (custom keyboard)
        if hasattr(message.reply_markup, "keyboard"):
            for row in message.reply_markup.keyboard:
                for btn in row:
                    btn_text = btn if isinstance(btn, str) else btn.text
                    if any(k in btn_text.lower() for k in keywords):
                        return btn_text, "reply"
    return None, None


async def click_button(app, chat_id, message, keywords, label=""):
    btn_text, btn_type = find_button(message, *keywords)
    if not btn_text:
        log.warning(f"Tombol '{label}' tidak ditemukan di pesan terakhir.")
        return False

    if btn_type == "inline":
        # cari lagi objek tombolnya buat ambil callback_data
        for row in message.reply_markup.inline_keyboard:
            for btn in row:
                if btn.text == btn_text:
                    await message.click(btn.text)
                    log.info(f"Klik tombol inline: {btn_text}")
                    return True
    elif btn_type == "reply":
        await app.send_message(chat_id, btn_text)
        log.info(f"Klik tombol keyboard: {btn_text}")
        return True

    return False


async def wait_new_message(app, chat_id, last_msg_id, timeout=WAIT_FOR_REPLY_TIMEOUT):
    """Poll pesan terbaru dari bot sampai ada pesan baru atau timeout."""
    elapsed = 0
    interval = 1.5
    while elapsed < timeout:
        async for msg in app.get_chat_history(chat_id, limit=1):
            if msg.id != last_msg_id:
                return msg
        await asyncio.sleep(interval)
        elapsed += interval
    return None


# ==================== MAIN FLOW ====================
async def run_account(session_string, data, index, total):
    tag = f"[{index}/{total}] {data['username']}"
    app = Client(
        name=f"acc_{index}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_string,
        in_memory=True,
    )

    try:
        await app.start()
        me = await app.get_me()
        log.info(f"{tag} Login sukses sebagai {me.first_name} (id={me.id})")

        # 1. Start bot dengan ref param
        await app.send_message(BOT_USERNAME, f"/start {START_PARAM}")
        await rand_delay(DELAY_BETWEEN_STEPS)
        last_msg = await wait_new_message_first(app, BOT_USERNAME)
        if not last_msg:
            log.error(f"{tag} Bot tidak merespon /start, skip akun ini.")
            await app.stop()
            return

        # 2. Captcha matematika
        answer = solve_math(last_msg.text or "")
        if answer is None:
            log.error(f"{tag} Gagal parse captcha dari: {last_msg.text!r}")
            await app.stop()
            return
        await app.send_message(BOT_USERNAME, str(answer))
        log.info(f"{tag} Jawab captcha: {answer}")
        await rand_delay(DELAY_BETWEEN_STEPS)
        last_msg = await wait_new_message(app, BOT_USERNAME, last_msg.id)
        if not last_msg:
            log.error(f"{tag} Tidak ada respon setelah captcha, skip.")
            await app.stop()
            return

        # 3. Klik "Submit your details"
        ok = await click_button(app, BOT_USERNAME, last_msg, ["submit your details", "submit"], "Submit your details")
        if not ok:
            log.error(f"{tag} Gagal klik Submit your details, skip.")
            await app.stop()
            return
        await rand_delay(DELAY_BETWEEN_STEPS)
        last_msg = await wait_new_message(app, BOT_USERNAME, last_msg.id)

        # 4. Isi link profile X
        profile_link = f"https://x.com/{data['username']}"
        await app.send_message(BOT_USERNAME, profile_link)
        log.info(f"{tag} Kirim profile X: {profile_link}")
        await rand_delay(DELAY_BETWEEN_STEPS)
        last_msg = await wait_new_message(app, BOT_USERNAME, last_msg.id)

        # 5. Isi email
        await app.send_message(BOT_USERNAME, data["email"])
        log.info(f"{tag} Kirim email: {data['email']}")
        await rand_delay(DELAY_BETWEEN_STEPS)
        last_msg = await wait_new_message(app, BOT_USERNAME, last_msg.id)

        # 6. Klik "Done"
        ok = await click_button(app, BOT_USERNAME, last_msg, ["done"], "Done #1")
        if not ok:
            log.warning(f"{tag} Tombol Done#1 tidak ketemu, coba lanjut.")
        await rand_delay(DELAY_BETWEEN_STEPS)
        last_msg = await wait_new_message(app, BOT_USERNAME, last_msg.id) or last_msg

        # 7. Klik "Done" lagi
        ok = await click_button(app, BOT_USERNAME, last_msg, ["done"], "Done #2")
        if not ok:
            log.warning(f"{tag} Tombol Done#2 tidak ketemu, coba lanjut.")
        await rand_delay(DELAY_BETWEEN_STEPS)
        last_msg = await wait_new_message(app, BOT_USERNAME, last_msg.id) or last_msg

        # 8. Isi link post X (fake, disesuaikan username, angka status di-random per akun)
        fake_status_id = random.randint(10**18, 9 * 10**18)
        post_link = f"https://x.com/{data['username']}/status/{fake_status_id}"
        await app.send_message(BOT_USERNAME, post_link)
        log.info(f"{tag} Kirim post X (fake): {post_link}")
        await rand_delay(DELAY_BETWEEN_STEPS)
        last_msg = await wait_new_message(app, BOT_USERNAME, last_msg.id)

        # 9. Klik "Yes"
        ok = await click_button(app, BOT_USERNAME, last_msg, ["yes"], "Yes")
        if not ok:
            log.warning(f"{tag} Tombol Yes tidak ketemu, coba lanjut.")
        await rand_delay(DELAY_BETWEEN_STEPS)
        last_msg = await wait_new_message(app, BOT_USERNAME, last_msg.id) or last_msg

        # 10. Submit wallet
        await app.send_message(BOT_USERNAME, data["wallet"])
        log.info(f"{tag} Kirim wallet: {data['wallet']}")
        await rand_delay(DELAY_BETWEEN_STEPS)
        last_msg = await wait_new_message(app, BOT_USERNAME, last_msg.id)

        # 11. Klik "Complete the airdrop"
        ok = await click_button(app, BOT_USERNAME, last_msg, ["complete the airdrop", "complete"], "Complete the airdrop")
        if ok:
            log.info(f"{tag} ✅ SELESAI submit airdrop.")
        else:
            log.warning(f"{tag} Tombol Complete tidak ketemu — cek manual, mungkin flow beda dikit.")

    except FloodWait as e:
        log.warning(f"{tag} FloodWait {e.value}s, tunggu...")
        await asyncio.sleep(e.value)
    except Exception as e:
        log.error(f"{tag} Error: {e}")
    finally:
        try:
            await app.stop()
        except Exception:
            pass


async def wait_new_message_first(app, chat_id, timeout=WAIT_FOR_REPLY_TIMEOUT):
    """Khusus dipakai setelah /start, ambil pesan terakhir apapun itu."""
    elapsed = 0
    interval = 1.5
    while elapsed < timeout:
        async for msg in app.get_chat_history(chat_id, limit=1):
            return msg
        await asyncio.sleep(interval)
        elapsed += interval
    return None


def select_range(total):
    """
    Tanya user mau proses akun yang mana:
      1. Satu akun aja (pilih index)
      2. Semua akun
      3. Dari index X sampai akhir
    Return (start_idx, end_idx) 0-based, inclusive end.
    """
    print(f"\nTotal akun terdeteksi: {total}")
    print("Pilih mode run:")
    print("  1. Satu akun")
    print("  2. Semua akun")
    print("  3. Dari akun ke-X sampai akhir")
    choice = input("Pilihan (1/2/3): ").strip()

    if choice == "1":
        idx = int(input(f"Akun ke berapa? (1-{total}): ").strip())
        idx = max(1, min(idx, total))
        return idx - 1, idx - 1
    elif choice == "3":
        start = int(input(f"Mulai dari akun ke berapa? (1-{total}): ").strip())
        start = max(1, min(start, total))
        return start - 1, total - 1
    else:
        return 0, total - 1


async def main():
    sessions = load_sessions(SESSIONS_FILE)
    data_rows = load_data(XPROFILE_FILE, WALLET_FILE, EMAIL_FILE)

    if len(sessions) != len(data_rows):
        log.warning(
            f"Jumlah sessions.txt ({len(sessions)}) dan data gabungan ({len(data_rows)}) beda! "
            f"Bakal dipasangin sesuai baris terpendek."
        )

    total = min(len(sessions), len(data_rows))
    if total == 0:
        log.error("Tidak ada akun yang bisa diproses. Cek isi file sessions/x_profile/wallet/email.")
        return

    start_idx, end_idx = select_range(total)
    log.info(f"Memproses akun ke-{start_idx + 1} sampai ke-{end_idx + 1} dari total {total}")

    for i in range(start_idx, end_idx + 1):
        await run_account(sessions[i], data_rows[i], i + 1, total)
        if i < end_idx:
            await rand_delay(DELAY_BETWEEN_ACCOUNTS)

    log.info("Selesai memproses akun yang dipilih.")


if __name__ == "__main__":
    asyncio.run(main())
