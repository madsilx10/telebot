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


async def ss_delay():
    t = round(random.uniform(2, 10), 1)
    print(f"    ⏳ nunggu respon bot... {t}s")
    await asyncio.sleep(t)


async def get_last_id(client, peer):
    async for msg in client.get_chat_history(peer, limit=1):
        return msg.id
    return 0


async def wait_button(client, peer, keyword,
                      after_id=0, timeout=60,
                      search_all=False, exclude_ids=None):
    """
    Poll sampai ketemu pesan dengan button mengandung keyword.
    exclude_ids : set msg.id yang sudah diklik, akan di-skip
    search_all  : abaikan after_id, cari di 15 pesan terakhir
    """
    if exclude_ids is None:
        exclude_ids = set()

    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(2)
        try:
            async for msg in client.get_chat_history(peer, limit=15):
                if not search_all and msg.id <= after_id:
                    break
                if msg.id in exclude_ids:
                    continue
                if not msg.reply_markup:
                    continue
                # inline keyboard
                if hasattr(msg.reply_markup, "inline_keyboard"):
                    for row in msg.reply_markup.inline_keyboard:
                        for btn in row:
                            if keyword.lower() in btn.text.lower():
                                return msg
                # reply keyboard
                if hasattr(msg.reply_markup, "keyboard"):
                    for row in msg.reply_markup.keyboard:
                        for btn in row:
                            text = btn.text if hasattr(btn, "text") else str(btn)
                            if keyword.lower() in text.lower():
                                return msg
        except Exception as e:
            print(f"    ⚠ poll error: {e}")
    return None


async def click_inline(msg, keyword):
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
    ok = await click_inline(msg, keyword)
    if not ok:
        ok = await send_reply_btn(client, peer, msg, keyword)
    if not ok:
        print(f"    ⚠ Tombol '{keyword}' tidak ditemukan")
    return ok


# ─────────────────────────────────────────────────────────────────────────────

async def run_account(session_name: str, x_username: str, ss_path: str, idx: int):
    print(f"\n{'='*40}")
    print(f"[{idx}] Proses akun...")

    async with Client(
        name=f"acc_{idx}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_name
    ) as client:
        try:
            me = await client.get_me()
            print(f"    👤 {me.first_name} (@{me.username})")

            clicked_ids = set()  # track msg id yang udah diklik verify

            # ── [1] START ─────────────────────────────────────────────────
            print("    [1] Start bot...")
            await client.send_message(BOT_USERNAME, f"/start {START_PARAM}")
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

            # ── [3] JOIN GRUP TELEGRAM ────────────────────────────────────
            print(f"    [3] Join grup @{GROUP}...")
            try:
                await client.join_chat(GROUP)
                print("    ✅ Joined!")
            except UserAlreadyParticipant:
                print("    ✅ Udah join sebelumnya")
            except Exception as e:
                print(f"    ⚠ Join error: {e}")

            # ── [4] VERIFY (join group) ───────────────────────────────────
            # search_all=True + exclude_ids supaya gak miss kalau bot edit pesan
            print("    [4] Klik Verify (join group)...")
            msg = await wait_button(
                client, BOT_USERNAME, "verify",
                after_id=0, timeout=30,
                search_all=True, exclude_ids=clicked_ids
            )
            if msg:
                await click_inline(msg, "verify")
                clicked_ids.add(msg.id)
                after_id = msg.id           # update after_id setelah klik
                await asyncio.sleep(3)      # tunggu bot kirim task berikutnya
            else:
                print("    ⚠ Tombol Verify (group) tidak ditemukan")

            # ── [5] VERIFY (di bawah Follow X) ───────────────────────────
            print("    [5] Klik Verify (Follow X task)...")
            msg = await wait_button(
                client, BOT_USERNAME, "verify",
                after_id=after_id, timeout=30,
                search_all=False            # cari pesan BARU setelah verify pertama
            )
            if msg:
                await click_inline(msg, "verify")
                clicked_ids.add(msg.id)
                after_id = msg.id           # update after_id
                await asyncio.sleep(2)      # tunggu bot minta X username
            else:
                print("    ⚠ Tombol Verify (X) tidak ditemukan")

            # ── [7] ISI X USERNAME ────────────────────────────────────────
            print(f"    [6] Kirim X username: {x_username}")
            await client.send_message(BOT_USERNAME, x_username)
            after_id = await get_last_id(client, BOT_USERNAME)

            # ── [8] SUBMIT WALLET ─────────────────────────────────────────
            # search_all=True karena tombol ini ada di reply keyboard persistent
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

            # ── [9] ALREADY INSTALLED ─────────────────────────────────────
            print("    [9] Klik Already Installed...")
            msg = await wait_button(
                client, BOT_USERNAME, "already",
                after_id=after_id, timeout=30,
                search_all=True             # teks asli ada backtick/newline, pakai search_all
            )
            if msg:
                await click_inline(msg, "already")
                after_id = msg.id
            else:
                print("    ⚠ Tombol Already Installed tidak ditemukan")

            # ── [10] KIRIM SCREENSHOT ─────────────────────────────────────
            print(f"    [10] Kirim screenshot: {ss_path}")
            if not os.path.exists(ss_path):
                print(f"    ❌ File tidak ada: {ss_path} — skip")
                return
            before_ss_id = await get_last_id(client, BOT_USERNAME)  # simpan SEBELUM kirim
            await client.send_photo(BOT_USERNAME, ss_path)
            await ss_delay()  # ← delay HANYA di sini

            # ── [11] TUNGGU & KLIK "YES, THAT'S MINE" ────────────────────
            print("    [11] Nunggu tombol 'Yes, that's mine'... (max 10 detik)")
            msg = await wait_button(
                client, BOT_USERNAME, "yes",
                after_id=before_ss_id, timeout=10   # pakai before_ss_id supaya tidak miss
            )
            if msg:
                await click_inline(msg, "yes")
                print(f"    🎉 [{idx}] SELESAI!")
            else:
                print("    ⚠ Tombol 'Yes' tidak muncul dalam 10 detik")

        except FloodWait as e:
            print(f"    ⏸ FloodWait: tunggu {e.value}s...")
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"    ❌ Error: {e}")
            traceback.print_exc()


# ─────────────────────────────────────────────────────────────────────────────

def pick_accounts(sessions, x_users):
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
        n = input(f"\nNomor akun (1–{total}): ").strip()
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
