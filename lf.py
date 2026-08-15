import asyncio
import random
import os
import traceback
from pyrogram import Client
from pyrogram.errors import FloodWait, UserAlreadyParticipant

# ── CONFIG ──────────────────────────────────────────────────────────────────
API_ID   = 12345678         # ← ganti
API_HASH = "your_api_hash"  # ← ganti

BOT_USERNAME = "LFWallet_AirdropBot"
START_PARAM  = "ref2005545171"
GROUP        = "LF_Wallet"
# ────────────────────────────────────────────────────────────────────────────


def load_file(path):
    with open(path, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]


async def rdelay(label=""):
    t = round(random.uniform(5, 15), 1)
    print(f"    ⏳ {label}delay {t}s...")
    await asyncio.sleep(t)


async def get_last_id(client, peer):
    async for msg in client.get_chat_history(peer, limit=1):
        return msg.id
    return 0


async def wait_button(client, peer, keyword,
                      after_id=0, timeout=60, search_all=False):
    """
    Poll chat history sampai ketemu pesan dengan button mengandung keyword.
    after_id  : hanya cari pesan dengan id > after_id (kecuali search_all=True)
    search_all: abaikan after_id, cari di semua 15 pesan terakhir
    """
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(2)
        try:
            async for msg in client.get_chat_history(peer, limit=15):
                if not search_all and msg.id <= after_id:
                    break
                if not msg.reply_markup:
                    continue
                # — inline keyboard —
                if hasattr(msg.reply_markup, "inline_keyboard"):
                    for row in msg.reply_markup.inline_keyboard:
                        for btn in row:
                            if keyword.lower() in btn.text.lower():
                                return msg
                # — reply keyboard —
                if hasattr(msg.reply_markup, "keyboard"):
                    for row in msg.reply_markup.keyboard:
                        for btn in row:
                            text = btn.text if hasattr(btn, "text") else str(btn)
                            if keyword.lower() in text.lower():
                                return msg
        except Exception as e:
            print(f"    ⚠ poll error: {e}")
        await asyncio.sleep(2)
    return None


async def click_inline(msg, keyword):
    """Klik inline button berdasarkan keyword teks."""
    if not msg or not msg.reply_markup:
        return False
    if not hasattr(msg.reply_markup, "inline_keyboard"):
        return False
    for row in msg.reply_markup.inline_keyboard:
        for btn in row:
            if keyword.lower() in btn.text.lower():
                try:
                    await msg.click(btn.text)
                    return True
                except Exception as e:
                    print(f"    ⚠ click error: {e}")
    return False


async def send_reply_btn(client, peer, msg, keyword):
    """Kirim teks reply keyboard button."""
    if not msg or not msg.reply_markup:
        return False
    if not hasattr(msg.reply_markup, "keyboard"):
        return False
    for row in msg.reply_markup.keyboard:
        for btn in row:
            text = btn.text if hasattr(btn, "text") else str(btn)
            if keyword.lower() in text.lower():
                await client.send_message(peer, text)
                return True
    return False


async def click_or_send(client, peer, msg, keyword):
    """Coba inline dulu, fallback ke reply keyboard."""
    ok = await click_inline(msg, keyword)
    if not ok:
        ok = await send_reply_btn(client, peer, msg, keyword)
    if not ok:
        print(f"    ⚠ Tombol '{keyword}' tidak ditemukan di pesan {msg.id}")
    return ok


# ─────────────────────────────────────────────────────────────────────────────

async def run_account(session_name: str, x_username: str, ss_path: str, idx: int):
    print(f"\n{'='*58}")
    print(f"[{idx}] Session : {session_name}")
    print(f"     X usn   : {x_username}")
    print(f"     SS      : {ss_path}")

    async with Client(session_name, api_id=API_ID, api_hash=API_HASH) as client:
        try:
            me = await client.get_me()
            print(f"    👤 {me.first_name} (@{me.username})")

            # ── [1] START ─────────────────────────────────────────────────
            print("    [1] /start bot...")
            await client.send_message(BOT_USERNAME, f"/start {START_PARAM}")
            await rdelay("start ")
            after_id = await get_last_id(client, BOT_USERNAME)

            # ── [2] KLIK TASKS ────────────────────────────────────────────
            print("    [2] Klik Tasks...")
            msg = await wait_button(
                client, BOT_USERNAME, "task",
                after_id=0, timeout=20, search_all=True
            )
            if msg:
                await click_or_send(client, BOT_USERNAME, msg, "task")
                after_id = msg.id
            else:
                print("    ⚠ Tombol Tasks tidak ditemukan")
            await rdelay("task ")

            # ── [3] KLIK JOIN GROUP ───────────────────────────────────────
            print("    [3] Klik Join Group...")
            msg = await wait_button(
                client, BOT_USERNAME, "join",
                after_id=after_id, timeout=30
            )
            if msg:
                await click_inline(msg, "join")
                after_id = msg.id
            else:
                print("    ⚠ Tombol Join tidak ditemukan")
            await rdelay("join btn ")

            # ── [4] JOIN GRUP TELEGRAM ────────────────────────────────────
            print(f"    [4] Join grup @{GROUP}...")
            try:
                await client.join_chat(GROUP)
                print("    ✅ Joined!")
            except UserAlreadyParticipant:
                print("    ✅ Udah join sebelumnya")
            except Exception as e:
                print(f"    ⚠ Join error: {e}")
            await rdelay("join grup ")

            # ── [5] VERIFY (join group) ───────────────────────────────────
            print("    [5] Klik Verify (join group)...")
            msg = await wait_button(
                client, BOT_USERNAME, "verify",
                after_id=after_id, timeout=30
            )
            if msg:
                await click_inline(msg, "verify")
                after_id = msg.id
            else:
                print("    ⚠ Tombol Verify (group) tidak ditemukan")
            await rdelay("verify1 ")

            # ── [6] VERIFY (di bawah Follow X) ───────────────────────────
            print("    [6] Klik Verify (Follow X task)...")
            msg = await wait_button(
                client, BOT_USERNAME, "verify",
                after_id=after_id, timeout=30
            )
            if msg:
                await click_inline(msg, "verify")
                after_id = msg.id
            else:
                print("    ⚠ Tombol Verify (X) tidak ditemukan")
            await rdelay("verify2 ")

            # ── [7] ISI X USERNAME ────────────────────────────────────────
            print(f"    [7] Kirim X username: {x_username}")
            await client.send_message(BOT_USERNAME, x_username)
            await rdelay("xusn ")
            after_id = await get_last_id(client, BOT_USERNAME)

            # ── [8] SUBMIT WALLET (di luar task menu) ─────────────────────
            # search_all=True karena "Submit Wallet" adalah tombol reply keyboard
            # yang udah ada dari awal (persistent), bukan pesan baru dari bot.
            # Beda dengan step [10] yang beneran send file foto.
            print("    [8] Klik Submit Wallet...")
            msg = await wait_button(
                client, BOT_USERNAME, "submit",
                after_id=0, timeout=30, search_all=True
            )
            if msg:
                await click_or_send(client, BOT_USERNAME, msg, "submit")
                after_id = msg.id
            else:
                print("    ⚠ Tombol Submit Wallet tidak ditemukan")
            await rdelay("submit ")

            # ── [9] ALREADY INSTALLED ─────────────────────────────────────
            print("    [9] Klik Already Installed...")
            msg = await wait_button(
                client, BOT_USERNAME, "installed",
                after_id=after_id, timeout=30
            )
            if msg:
                await click_inline(msg, "installed")
                after_id = msg.id
            else:
                print("    ⚠ Tombol Already Installed tidak ditemukan")
            await rdelay("installed ")

            # ── [10] KIRIM SCREENSHOT ─────────────────────────────────────
            print(f"    [10] Kirim screenshot: {ss_path}")
            if not os.path.exists(ss_path):
                print(f"    ❌ File tidak ada: {ss_path} — skip akun ini")
                return
            await client.send_photo(BOT_USERNAME, ss_path)
            await rdelay("ss ")
            after_id = await get_last_id(client, BOT_USERNAME)

            # ── [11] TUNGGU & KLIK "YES, THAT'S MINE" ────────────────────
            print("    [11] Nunggu tombol 'Yes, that's mine'... (max 2 menit)")
            msg = await wait_button(
                client, BOT_USERNAME, "yes",
                after_id=after_id, timeout=120
            )
            if msg:
                await click_inline(msg, "yes")
                print(f"    🎉 [{idx}] SELESAI!")
            else:
                print("    ⚠ Tombol 'Yes' tidak muncul dalam 2 menit")

        except FloodWait as e:
            print(f"    ⏸ FloodWait: tunggu {e.value}s...")
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"    ❌ Error: {e}")
            traceback.print_exc()


# ─────────────────────────────────────────────────────────────────────────────

def pick_accounts(sessions, x_users):
    """
    Menu pilihan akun. Return list of (index_1based, session, xusn).
    """
    total = len(sessions)

    print("\n┌─────────────────────────────────┐")
    print("│     LFWallet Bot — Pilih Akun   │")
    print("├─────────────────────────────────┤")
    print("│  1. Satu akun                   │")
    print("│  2. Semua akun                  │")
    print("│  3. Dari akun X sampai akhir    │")
    print("└─────────────────────────────────┘")
    print(f"   Total akun tersedia: {total}")

    choice = input("\nPilih (1/2/3): ").strip()

    if choice == "1":
        print(f"\nAkun tersedia (1–{total}):")
        for i, s in enumerate(sessions, 1):
            print(f"  {i}. {s}")
        n = input("Pilih nomor akun: ").strip()
        try:
            idx = int(n)
            if not (1 <= idx <= total):
                raise ValueError
        except ValueError:
            print("❌ Nomor tidak valid")
            return []
        return [(idx, sessions[idx-1], x_users[idx-1])]

    elif choice == "2":
        return [(i, sessions[i-1], x_users[i-1]) for i in range(1, total+1)]

    elif choice == "3":
        n = input(f"Mulai dari akun nomor (1–{total}): ").strip()
        try:
            start = int(n)
            if not (1 <= start <= total):
                raise ValueError
        except ValueError:
            print("❌ Nomor tidak valid")
            return []
        return [(i, sessions[i-1], x_users[i-1]) for i in range(start, total+1)]

    else:
        print("❌ Pilihan tidak valid")
        return []


async def main():
    sessions = load_file("sessions.txt")
    x_users  = load_file("xusn.txt")

    if len(sessions) != len(x_users):
        print(f"❌ Jumlah session ({len(sessions)}) ≠ xusn ({len(x_users)})")
        return

    queue = pick_accounts(sessions, x_users)
    if not queue:
        return

    print(f"\n🚀 Akan proses {len(queue)} akun...")

    for pos, (idx, sess, xusn) in enumerate(queue):
        await run_account(sess, xusn, f"ss/{idx}.jpg", idx)
        if pos < len(queue) - 1:
            gap = round(random.uniform(15, 30), 1)
            print(f"\n⏳ Jeda antar akun: {gap}s...")
            await asyncio.sleep(gap)

    print("\n✅ Semua akun selesai!")


if __name__ == "__main__":
    asyncio.run(main())
