import asyncio
import random
import re
import string
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.errors import FloodWait, UserAlreadyParticipant
from pyrogram.raw.functions.messages import StartBot
from pyrogram.raw.types import InputPeerUser, InputUser

# ─── CONFIG ───────────────────────────────────────────────────────────────────
API_ID   = 0         # ganti
API_HASH = ""        # ganti

BOT_USERNAME  = "EightlendsAirdropBot"
BOT_STARTPARAM = "ref_2005545171"
GROUP_USERNAME = "eightlends_korea"

TIMEOUT = 60  # detik nunggu reply bot
# ──────────────────────────────────────────────────────────────────────────────


def load_lines(path: str) -> list[str]:
    with open(path, "r") as f:
        return [l.strip() for l in f if l.strip()]


def parse_username(x_profile: str) -> str:
    """Ambil username dari link X profile."""
    # https://x.com/username  atau  https://twitter.com/username
    parts = x_profile.rstrip("/").split("/")
    return parts[-1]


def gen_repost_link(username: str) -> str:
    """Format: https://x.com/{username}/status/20xxxxxxxxxxxxxxxx"""
    suffix = "".join(random.choices(string.digits, k=17))
    return f"https://x.com/{username}/status/20{suffix}"


def solve_captcha(text: str) -> str | None:
    """Parse dan selesaikan soal matematika sederhana dari teks bot."""
    match = re.search(r"(\d+)\s*([+\-*x×])\s*(\d+)", text)
    if not match:
        return None
    a, op, b = int(match.group(1)), match.group(2), int(match.group(3))
    if op == "+":
        return str(a + b)
    elif op == "-":
        return str(a - b)
    elif op in ("*", "x", "×"):
        return str(a * b)
    return None


async def wait_reply(client: Client, bot_id: int, timeout: int = TIMEOUT) -> Message | None:
    """Tunggu pesan baru dari bot dalam timeout detik."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        async for msg in client.get_chat_history(bot_id, limit=1):
            return msg
        await asyncio.sleep(1)
    return None


async def wait_new_message(client: Client, bot_id: int, after_id: int, timeout: int = TIMEOUT) -> Message | None:
    """Tunggu pesan baru dari bot setelah message_id tertentu."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        async for msg in client.get_chat_history(bot_id, limit=1):
            if msg.id > after_id:
                return msg
            break
        await asyncio.sleep(1.5)
    return None


async def click_button(client: Client, msg: Message, keyword: str) -> bool:
    """Klik inline button yang mengandung keyword (case-insensitive)."""
    if not msg.reply_markup:
        return False
    for row in msg.reply_markup.inline_keyboard:
        for btn in row:
            if keyword.lower() in btn.text.lower():
                await msg.click(btn.text)
                return True
    return False


async def run_account(
    session_str: str,
    x_profile: str,
    email: str,
    wallet: str,
    index: int
):
    username = parse_username(x_profile)
    repost_link = gen_repost_link(username)
    label = f"[Akun {index+1}]"

    client = Client(
        name=f"session_{index}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_str,
        in_memory=True,
    )

    async with client:
        print(f"{label} Login OK → {await client.get_me().then(lambda u: u.username) if False else (await client.get_me()).username}")

        # ── 1. Resolve bot ──────────────────────────────────────────────────
        bot_entity = await client.resolve_peer(BOT_USERNAME)
        bot_id     = bot_entity.user_id if hasattr(bot_entity, "user_id") else bot_entity.channel_id

        # ── 2. /start dengan deep link ──────────────────────────────────────
        print(f"{label} Sending /start ...")
        await client.invoke(
            StartBot(
                bot=InputUser(user_id=bot_entity.user_id, access_hash=bot_entity.access_hash),
                peer=InputPeerUser(user_id=bot_entity.user_id, access_hash=bot_entity.access_hash),
                random_id=random.randint(1, 2**32),
                start_param=BOT_STARTPARAM,
            )
        )
        await asyncio.sleep(3)

        # ── 3. Ambil pesan pertama dari bot ─────────────────────────────────
        last_msg = None
        async for msg in client.get_chat_history(BOT_USERNAME, limit=1):
            last_msg = msg
            break

        if not last_msg:
            print(f"{label} ❌ Ga ada reply dari bot setelah /start")
            return

        # ── 4. Jawab captcha ─────────────────────────────────────────────────
        if any(op in last_msg.text for op in ["+", "-", "*", "×", "x"]) and re.search(r"\d", last_msg.text):
            answer = solve_captcha(last_msg.text)
            if not answer:
                print(f"{label} ❌ Gagal parse captcha: {last_msg.text!r}")
                return
            print(f"{label} Captcha: {last_msg.text.strip()!r} → Jawaban: {answer}")
            prev_id = last_msg.id
            await client.send_message(BOT_USERNAME, answer)
            await asyncio.sleep(2)
            last_msg = await wait_new_message(client, BOT_USERNAME, prev_id)
            if not last_msg:
                print(f"{label} ❌ Timeout setelah jawab captcha")
                return
            print(f"{label} Reply captcha: {last_msg.text[:80] if last_msg.text else '(no text)'}")
        else:
            print(f"{label} ⚠️ Captcha tidak terdeteksi, lanjut ...")

        # ── 5. Join group ────────────────────────────────────────────────────
        print(f"{label} Join group @{GROUP_USERNAME} ...")
        try:
            await client.join_chat(GROUP_USERNAME)
            print(f"{label} ✅ Joined group")
        except UserAlreadyParticipant:
            print(f"{label} Sudah join group")
        except Exception as e:
            print(f"{label} ⚠️ Join group error: {e}")
        await asyncio.sleep(2)

        # ── 6. Klik "Submit your details" ───────────────────────────────────
        print(f"{label} Klik 'Submit your details' ...")
        # Refresh pesan terbaru
        async for msg in client.get_chat_history(BOT_USERNAME, limit=1):
            last_msg = msg
            break

        clicked = await click_button(client, last_msg, "submit your details")
        if not clicked:
            # Coba beberapa pesan terakhir
            async for msg in client.get_chat_history(BOT_USERNAME, limit=5):
                if await click_button(client, msg, "submit your details"):
                    clicked = True
                    last_msg = msg
                    break
        if not clicked:
            print(f"{label} ❌ Tombol 'Submit your details' tidak ditemukan")
            return
        await asyncio.sleep(2)

        # ── 7. Isi X profile ─────────────────────────────────────────────────
        prev_id = last_msg.id
        last_msg = await wait_new_message(client, BOT_USERNAME, prev_id)
        if not last_msg:
            print(f"{label} ❌ Timeout nunggu prompt X profile")
            return
        print(f"{label} Bot: {last_msg.text[:80] if last_msg.text else ''}")
        print(f"{label} Kirim X profile: {x_profile}")
        prev_id = last_msg.id
        await client.send_message(BOT_USERNAME, x_profile)
        await asyncio.sleep(2)

        # ── 8. Isi email pertama ─────────────────────────────────────────────
        last_msg = await wait_new_message(client, BOT_USERNAME, prev_id)
        if not last_msg:
            print(f"{label} ❌ Timeout nunggu prompt email")
            return
        print(f"{label} Bot: {last_msg.text[:80] if last_msg.text else ''}")
        print(f"{label} Kirim email: {email}")
        prev_id = last_msg.id
        await client.send_message(BOT_USERNAME, email)
        await asyncio.sleep(2)

        # ── 9. Klik "Done" ───────────────────────────────────────────────────
        last_msg = await wait_new_message(client, BOT_USERNAME, prev_id)
        if not last_msg:
            print(f"{label} ❌ Timeout nunggu tombol Done")
            return
        print(f"{label} Bot: {last_msg.text[:80] if last_msg.text else ''}")
        clicked = await click_button(client, last_msg, "done")
        if not clicked:
            print(f"{label} ❌ Tombol 'Done' tidak ditemukan")
            return
        print(f"{label} ✅ Klik Done")
        await asyncio.sleep(2)

        # ── 10. Isi repost link ──────────────────────────────────────────────
        prev_id = last_msg.id
        last_msg = await wait_new_message(client, BOT_USERNAME, prev_id)
        if not last_msg:
            print(f"{label} ❌ Timeout nunggu prompt repost link")
            return
        print(f"{label} Bot: {last_msg.text[:80] if last_msg.text else ''}")
        print(f"{label} Kirim repost link: {repost_link}")
        prev_id = last_msg.id
        await client.send_message(BOT_USERNAME, repost_link)
        await asyncio.sleep(2)

        # ── 11. Klik "Yes" ───────────────────────────────────────────────────
        last_msg = await wait_new_message(client, BOT_USERNAME, prev_id)
        if not last_msg:
            print(f"{label} ❌ Timeout nunggu tombol Yes")
            return
        print(f"{label} Bot: {last_msg.text[:80] if last_msg.text else ''}")
        clicked = await click_button(client, last_msg, "yes")
        if not clicked:
            print(f"{label} ❌ Tombol 'Yes' tidak ditemukan")
            return
        print(f"{label} ✅ Klik Yes")
        await asyncio.sleep(2)

        # ── 12. Isi email kedua ──────────────────────────────────────────────
        prev_id = last_msg.id
        last_msg = await wait_new_message(client, BOT_USERNAME, prev_id)
        if not last_msg:
            print(f"{label} ❌ Timeout nunggu prompt email ke-2")
            return
        print(f"{label} Bot: {last_msg.text[:80] if last_msg.text else ''}")
        print(f"{label} Kirim email (ke-2): {email}")
        prev_id = last_msg.id
        await client.send_message(BOT_USERNAME, email)
        await asyncio.sleep(2)

        # ── 13. Isi wallet ───────────────────────────────────────────────────
        last_msg = await wait_new_message(client, BOT_USERNAME, prev_id)
        if not last_msg:
            print(f"{label} ❌ Timeout nunggu prompt wallet")
            return
        print(f"{label} Bot: {last_msg.text[:80] if last_msg.text else ''}")
        print(f"{label} Kirim wallet: {wallet}")
        prev_id = last_msg.id
        await client.send_message(BOT_USERNAME, wallet)
        await asyncio.sleep(2)

        # ── 14. Klik "Complete the airdrop" ─────────────────────────────────
        last_msg = await wait_new_message(client, BOT_USERNAME, prev_id)
        if not last_msg:
            print(f"{label} ❌ Timeout nunggu tombol Complete")
            return
        print(f"{label} Bot: {last_msg.text[:80] if last_msg.text else ''}")
        clicked = await click_button(client, last_msg, "complete the airdrop")
        if not clicked:
            print(f"{label} ❌ Tombol 'Complete the airdrop' tidak ditemukan")
            return
        print(f"{label} ✅ Klik Complete the airdrop")
        await asyncio.sleep(2)

        # ── 15. Konfirmasi akhir ─────────────────────────────────────────────
        prev_id = last_msg.id
        last_msg = await wait_new_message(client, BOT_USERNAME, prev_id, timeout=15)
        if last_msg and last_msg.text:
            print(f"{label} 🎉 Reply akhir: {last_msg.text[:150]}")
        print(f"{label} ✅ SELESAI\n")


async def main():
    sessions  = load_lines("sessions.txt")
    x_profiles = load_lines("x_profile.txt")
    emails    = load_lines("email.txt")
    wallets   = load_lines("wallet.txt")

    total = len(sessions)
    print(f"Total akun: {total}\n")

    print("Pilih mode:")
    print("  1 = 1 akun")
    print("  2 = semua akun")
    print("  3 = from X to end")
    mode = input("Pilihan [1/2/3]: ").strip()

    if mode == "1":
        idx = int(input(f"Nomor akun [1-{total}]: ").strip()) - 1
        indices = [idx]
    elif mode == "2":
        indices = list(range(total))
    elif mode == "3":
        start = int(input(f"Mulai dari akun nomor [1-{total}]: ").strip()) - 1
        indices = list(range(start, total))
    else:
        print("Pilihan tidak valid.")
        return

    print(f"\nJalanin {len(indices)} akun: {[i+1 for i in indices]}\n")

    for i in indices:
        try:
            await run_account(
                session_str=sessions[i],
                x_profile=x_profiles[i],
                email=emails[i],
                wallet=wallets[i],
                index=i,
            )
        except FloodWait as e:
            print(f"[Akun {i+1}] ⚠️ FloodWait {e.value}s, tunggu ...")
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"[Akun {i+1}] ❌ Error: {e}")

        if i != indices[-1]:
            delay = random.randint(5, 10)
            print(f"Delay {delay}s sebelum akun berikutnya ...\n")
            await asyncio.sleep(delay)


if __name__ == "__main__":
    asyncio.run(main())
