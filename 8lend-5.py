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

BOT_USERNAME   = "EightlendsAirdropBot"
BOT_STARTPARAM = "ref_2005545171"
GROUP_USERNAME = "eightlends_korea"

TIMEOUT = 60
# ──────────────────────────────────────────────────────────────────────────────


def load_lines(path: str) -> list[str]:
    with open(path, "r") as f:
        return [l.strip() for l in f if l.strip()]


def parse_username(x_profile: str) -> str:
    parts = x_profile.rstrip("/").split("/")
    return parts[-1]


def gen_repost_link(username: str) -> str:
    suffix = "".join(random.choices(string.digits, k=17))
    return f"https://x.com/{username}/status/20{suffix}"


def solve_captcha(text: str) -> str | None:
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


async def wait_new_message(client: Client, chat: str, after_id: int, timeout: int = TIMEOUT) -> Message | None:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        async for msg in client.get_chat_history(chat, limit=1):
            if msg.id > after_id:
                return msg
            break
        await asyncio.sleep(1.5)
    return None


async def click_button(client: Client, chat: str, msg: Message, keyword: str) -> bool:
    if not msg.reply_markup:
        return False
    markup = msg.reply_markup
    if hasattr(markup, "keyboard"):
        for row in markup.keyboard:
            for btn in row:
                text = btn.text if hasattr(btn, "text") else str(btn)
                if keyword.lower() in text.lower():
                    await client.send_message(chat, text)
                    return True
    if hasattr(markup, "inline_keyboard"):
        for row in markup.inline_keyboard:
            for btn in row:
                if keyword.lower() in btn.text.lower():
                    await msg.click(btn.text)
                    return True
    return False


async def do_join_and_complete(client: Client, label: str):
    """Step join extra group + klik complete the airdrop."""

    # Join salah satu extra group
    for extra_group in ["AirdropDetectiveGroup", "Bounties"]:
        try:
            await client.join_chat(extra_group)
            print(f"{label} ✅ Join @{extra_group}")
            break
        except UserAlreadyParticipant:
            print(f"{label} Sudah join @{extra_group}")
            break
        except Exception as e:
            print(f"{label} ⚠️ Gagal join @{extra_group}: {e}, coba berikutnya ...")
    await asyncio.sleep(2)

    # Ambil pesan terakhir dari bot
    last_msg = None
    async for msg in client.get_chat_history(BOT_USERNAME, limit=1):
        last_msg = msg
        break

    if not last_msg:
        print(f"{label} ❌ Ga ada pesan dari bot")
        return

    # Klik complete the airdrop
    clicked = False
    async for msg in client.get_chat_history(BOT_USERNAME, limit=5):
        if await click_button(client, BOT_USERNAME, msg, "complete the airdrop"):
            last_msg = msg
            clicked = True
            break

    if not clicked:
        print(f"{label} ❌ Tombol 'Complete the airdrop' tidak ditemukan")
        return
    print(f"{label} ✅ Klik Complete the airdrop")
    await asyncio.sleep(2)

    # Reply akhir
    prev_id  = last_msg.id
    last_msg = await wait_new_message(client, BOT_USERNAME, prev_id, timeout=15)
    if last_msg and last_msg.text:
        print(f"{label} 🎉 {last_msg.text[:150]}")
    print(f"{label} ✅ SELESAI\n")


async def run_complete_only(session_str: str, index: int):
    """Mode 4: langsung join group + complete, skip flow awal."""
    label  = f"[Akun {index+1}]"
    client = Client(
        name=f"session_{index}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_str,
        in_memory=True,
    )
    async with client:
        me = await client.get_me()
        print(f"{label} Login OK → @{me.username or me.first_name}")
        await do_join_and_complete(client, label)


async def run_account(session_str: str, x_profile: str, email: str, wallet: str, index: int):
    """Mode 1-3: full flow dari awal."""
    username    = parse_username(x_profile)
    repost_link = gen_repost_link(username)
    label       = f"[Akun {index+1}]"

    client = Client(
        name=f"session_{index}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_str,
        in_memory=True,
    )

    async with client:
        me = await client.get_me()
        print(f"{label} Login OK → @{me.username or me.first_name}")

        # ── 1. Resolve bot ──────────────────────────────────────────────────
        bot_peer = await client.resolve_peer(BOT_USERNAME)

        # ── 2. /start dengan deep link ──────────────────────────────────────
        print(f"{label} Sending /start ...")
        await client.invoke(
            StartBot(
                bot=InputUser(user_id=bot_peer.user_id, access_hash=bot_peer.access_hash),
                peer=InputPeerUser(user_id=bot_peer.user_id, access_hash=bot_peer.access_hash),
                random_id=random.randint(1, 2**32),
                start_param=BOT_STARTPARAM,
            )
        )
        await asyncio.sleep(3)

        # ── 3. Ambil pesan pertama ───────────────────────────────────────────
        last_msg = None
        async for msg in client.get_chat_history(BOT_USERNAME, limit=1):
            last_msg = msg
            break

        if not last_msg:
            print(f"{label} ❌ Ga ada reply dari bot setelah /start")
            return

        # ── 4. Jawab captcha ─────────────────────────────────────────────────
        txt = last_msg.text or ""
        if re.search(r"\d+\s*[+\-*x×]\s*\d+", txt):
            answer = solve_captcha(txt)
            if not answer:
                print(f"{label} ❌ Gagal parse captcha: {txt!r}")
                return
            print(f"{label} Captcha: {txt.strip()!r} → {answer}")
            prev_id = last_msg.id
            await client.send_message(BOT_USERNAME, answer)
            await asyncio.sleep(2)
            last_msg = await wait_new_message(client, BOT_USERNAME, prev_id)
            if not last_msg:
                print(f"{label} ❌ Timeout setelah jawab captcha")
                return
            print(f"{label} Reply: {(last_msg.text or '')[:80]}")
        else:
            print(f"{label} ⚠️ Captcha tidak terdeteksi, lanjut ...")

        # ── 5. Join group ────────────────────────────────────────────────────
        print(f"{label} Join @{GROUP_USERNAME} ...")
        try:
            await client.join_chat(GROUP_USERNAME)
            print(f"{label} ✅ Joined")
        except UserAlreadyParticipant:
            print(f"{label} Sudah join")
        except Exception as e:
            print(f"{label} ⚠️ Join error: {e}")
        await asyncio.sleep(2)

        # ── 6. Klik "Submit your details" ───────────────────────────────────
        print(f"{label} Klik 'Submit your details' ...")
        clicked = False
        async for msg in client.get_chat_history(BOT_USERNAME, limit=5):
            if await click_button(client, BOT_USERNAME, msg, "submit your details"):
                last_msg = msg
                clicked  = True
                break
        if not clicked:
            print(f"{label} ❌ Tombol 'Submit your details' tidak ditemukan")
            return
        await asyncio.sleep(2)

        # ── 7. Isi X profile ─────────────────────────────────────────────────
        prev_id  = last_msg.id
        last_msg = await wait_new_message(client, BOT_USERNAME, prev_id)
        if not last_msg:
            print(f"{label} ❌ Timeout nunggu prompt X profile")
            return
        print(f"{label} Bot: {(last_msg.text or '')[:80]}")
        print(f"{label} Kirim X profile: {x_profile}")
        prev_id = last_msg.id
        await client.send_message(BOT_USERNAME, x_profile)
        await asyncio.sleep(2)

        # ── 8. Isi email pertama ─────────────────────────────────────────────
        last_msg = await wait_new_message(client, BOT_USERNAME, prev_id)
        if not last_msg:
            print(f"{label} ❌ Timeout nunggu prompt email")
            return
        print(f"{label} Bot: {(last_msg.text or '')[:80]}")
        print(f"{label} Kirim email: {email}")
        prev_id = last_msg.id
        await client.send_message(BOT_USERNAME, email)
        await asyncio.sleep(2)

        # ── 9. Klik "Done" ───────────────────────────────────────────────────
        last_msg = await wait_new_message(client, BOT_USERNAME, prev_id)
        if not last_msg:
            print(f"{label} ❌ Timeout nunggu tombol Done")
            return
        print(f"{label} Bot: {(last_msg.text or '')[:80]}")
        if not await click_button(client, BOT_USERNAME, last_msg, "done"):
            print(f"{label} ❌ Tombol 'Done' tidak ditemukan")
            return
        print(f"{label} ✅ Klik Done")
        await asyncio.sleep(2)

        # ── 10. Isi repost link ──────────────────────────────────────────────
        prev_id  = last_msg.id
        last_msg = await wait_new_message(client, BOT_USERNAME, prev_id)
        if not last_msg:
            print(f"{label} ❌ Timeout nunggu prompt repost link")
            return
        print(f"{label} Bot: {(last_msg.text or '')[:80]}")
        print(f"{label} Kirim repost: {repost_link}")
        prev_id = last_msg.id
        await client.send_message(BOT_USERNAME, repost_link)
        await asyncio.sleep(2)

        # ── 11. Klik "Yes" ───────────────────────────────────────────────────
        last_msg = await wait_new_message(client, BOT_USERNAME, prev_id)
        if not last_msg:
            print(f"{label} ❌ Timeout nunggu tombol Yes")
            return
        print(f"{label} Bot: {(last_msg.text or '')[:80]}")
        if not await click_button(client, BOT_USERNAME, last_msg, "yes"):
            print(f"{label} ❌ Tombol 'Yes' tidak ditemukan")
            return
        print(f"{label} ✅ Klik Yes")
        await asyncio.sleep(2)

        # ── 12. Isi email kedua ──────────────────────────────────────────────
        prev_id  = last_msg.id
        last_msg = await wait_new_message(client, BOT_USERNAME, prev_id)
        if not last_msg:
            print(f"{label} ❌ Timeout nunggu prompt email ke-2")
            return
        print(f"{label} Bot: {(last_msg.text or '')[:80]}")
        print(f"{label} Kirim email (ke-2): {email}")
        prev_id = last_msg.id
        await client.send_message(BOT_USERNAME, email)
        await asyncio.sleep(2)

        # ── 13. Isi wallet ───────────────────────────────────────────────────
        last_msg = await wait_new_message(client, BOT_USERNAME, prev_id)
        if not last_msg:
            print(f"{label} ❌ Timeout nunggu prompt wallet")
            return
        print(f"{label} Bot: {(last_msg.text or '')[:80]}")
        print(f"{label} Kirim wallet: {wallet}")
        prev_id = last_msg.id
        await client.send_message(BOT_USERNAME, wallet)
        await asyncio.sleep(2)

        # ── 14-16. Join extra group + complete ───────────────────────────────
        await do_join_and_complete(client, label)


async def pick_indices(total: int) -> list[int]:
    print("  1 = 1 akun")
    print("  2 = semua")
    print("  3 = from X to end")
    sub = input("Pilih akun [1/2/3]: ").strip()
    if sub == "1":
        idx = int(input(f"Nomor akun [1-{total}]: ").strip()) - 1
        return [idx]
    elif sub == "2":
        return list(range(total))
    elif sub == "3":
        start = int(input(f"Mulai dari akun nomor [1-{total}]: ").strip()) - 1
        return list(range(start, total))
    else:
        print("Pilihan tidak valid.")
        return []


async def main():
    sessions   = load_lines("sessions.txt")
    x_profiles = load_lines("x_profile.txt")
    emails     = load_lines("email.txt")
    wallets    = load_lines("wallet.txt")

    total = len(sessions)
    print(f"Total akun: {total}\n")
    print("Pilih mode:")
    print("  1 = all (full flow dari awal)")
    print("  2 = complete only (join group + complete)")
    mode = input("Pilihan [1/2]: ").strip()

    if mode not in ("1", "2"):
        print("Pilihan tidak valid.")
        return

    print()
    indices = await pick_indices(total)
    if not indices:
        return

    print(f"\nJalanin {len(indices)} akun: {[i+1 for i in indices]}\n")

    for i in indices:
        try:
            if mode == "2":
                await run_complete_only(session_str=sessions[i], index=i)
            else:
                await run_account(
                    session_str=sessions[i],
                    x_profile=x_profiles[i],
                    email=emails[i],
                    wallet=wallets[i],
                    index=i,
                )
        except FloodWait as e:
            print(f"[Akun {i+1}] ⚠️ FloodWait {e.value}s ...")
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"[Akun {i+1}] ❌ Error: {e}")

        if i != indices[-1]:
            delay = random.randint(5, 10)
            print(f"Delay {delay}s ...\n")
            await asyncio.sleep(delay)


if __name__ == "__main__":
    asyncio.run(main())
