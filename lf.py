import asyncio
import random
import os
import traceback
import requests
from pyrogram import Client
from pyrogram.errors import FloodWait, UserAlreadyParticipant

# ── CONFIG ──────────────────────────────────────────────────────────────────
API_ID   = 12345678         # ← ganti
API_HASH = "your_api_hash"  # ← ganti

BOT_USERNAME = "LFWallet_AirdropBot"
START_PARAM  = "ref2005545171"
GROUP        = "LF_Wallet"

TARGET_X_USERNAME = "LFWallet"
X_BEARER = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
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


async def click_inline(msg, keyword, nth=1):
    if not msg or not msg.reply_markup:
        return False
    if not hasattr(msg.reply_markup, "inline_keyboard"):
        return False
    count = 0
    for row in msg.reply_markup.inline_keyboard:
        for btn in row:
            if keyword.lower() in btn.text.lower():
                count += 1
                if count == nth:
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

async def run_account(session_name: str, x_username: str, discord_username: str, ss_path: str, idx: int):
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
                await asyncio.sleep(3)      # tunggu bot edit/kirim pesan

                # ── DEBUG: print semua tombol di 5 pesan terakhir ──────────
                print("    [DEBUG] Scan tombol setelah verify #1:")
                async for m in client.get_chat_history(BOT_USERNAME, limit=5):
                    if not m.reply_markup:
                        continue
                    if hasattr(m.reply_markup, "inline_keyboard"):
                        print(f"      msg_id={m.id} [inline]:")
                        for row in m.reply_markup.inline_keyboard:
                            for btn in row:
                                print(f"        {repr(btn.text)}")
                    if hasattr(m.reply_markup, "keyboard"):
                        print(f"      msg_id={m.id} [reply]:")
                        for row in m.reply_markup.keyboard:
                            for btn in row:
                                t = btn.text if hasattr(btn, "text") else str(btn)
                                print(f"        {repr(t)}")
                # ───────────────────────────────────────────────────────────

            else:
                print("    ⚠ Tombol Verify (group) tidak ditemukan")

            # ── [5] VERIFY (di bawah Follow X) ───────────────────────────
            # search_all=True tanpa exclude_ids:
            # bot kemungkinan EDIT pesan task yang sama (ID sama),
            # jadi tidak bisa pakai after_id filter atau exclude_ids
            print("    [5] Klik Verify (Follow X task)...")
            msg = await wait_button(
                client, BOT_USERNAME, "verify",
                after_id=0, timeout=30,
                search_all=True, exclude_ids=set()
            )
            if msg:
                await click_inline(msg, "verify", nth=1)   # setelah edit: satu-satunya verify = Follow X
                clicked_ids.add(msg.id)
                after_id = msg.id
                await asyncio.sleep(2)
            else:
                print("    ⚠ Tombol Verify (X) tidak ditemukan")

            # ── [7] ISI X USERNAME ────────────────────────────────────────
            print(f"    [6] Kirim X username: {x_username}")
            await client.send_message(BOT_USERNAME, x_username)
            after_id = await get_last_id(client, BOT_USERNAME)

            # ── [7] VERIFY (di bawah task Discord) ───────────────────────
            # tombol verify khusus task Discord, beda sama verify sebelumnya
            print("    [7] Klik Verify (Discord task)...")
            msg = await wait_button(
                client, BOT_USERNAME, "verify",
                after_id=0, timeout=30,
                search_all=True, exclude_ids=clicked_ids
            )
            if msg:
                await click_inline(msg, "verify", nth=1)
                clicked_ids.add(msg.id)
                after_id = msg.id
                await asyncio.sleep(2)
            else:
                print("    ⚠ Tombol Verify (Discord) tidak ditemukan")

            # ── [7b] SUBMIT USN DISCORD ───────────────────────────────────
            print(f"    [7b] Kirim USN Discord: {discord_username}")
            await client.send_message(BOT_USERNAME, discord_username)
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
# MODE BARU: submit usn discord doang, ga perlu start dari awal
# ─────────────────────────────────────────────────────────────────────────────

async def run_usn_discord_only(session_name: str, discord_username: str, idx: int):
    print(f"\n{'='*40}")
    print(f"[{idx}] Proses akun (mode: Submit USN Discord)...")

    async with Client(
        name=f"acc_{idx}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_name
    ) as client:
        try:
            me = await client.get_me()
            print(f"    👤 {me.first_name} (@{me.username})")

            # ── [1] KLIK TASKS (dari histori chat, gak start sama sekali) ──
            print("    [1] Cari & klik Tasks di histori chat...")
            msg = await wait_button(
                client, BOT_USERNAME, "task",
                after_id=0, timeout=20, search_all=True
            )
            if msg:
                await click_or_send(client, BOT_USERNAME, msg, "task")
                after_id = msg.id
            else:
                print("    ⚠ Tombol Tasks gak ketemu di histori — skip (gak /start biar ga reset)")

            # ── [2] VERIFY (task Discord) ──────────────────────────────────
            print("    [2] Klik Verify (Discord task)...")
            msg = await wait_button(
                client, BOT_USERNAME, "verify",
                after_id=0, timeout=30,
                search_all=True, exclude_ids=set()
            )
            if msg:
                await click_inline(msg, "verify", nth=1)
                after_id = msg.id
                await asyncio.sleep(2)
            else:
                print("    ⚠ Tombol Verify (Discord) tidak ditemukan")

            # ── [3] SUBMIT USN DISCORD ──────────────────────────────────────
            print(f"    [3] Kirim USN Discord: {discord_username}")
            await client.send_message(BOT_USERNAME, discord_username)
            print(f"    🎉 [{idx}] SELESAI!")

        except FloodWait as e:
            print(f"    ⏸ FloodWait: tunggu {e.value}s...")
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"    ❌ Error: {e}")
            traceback.print_exc()


# ─────────────────────────────────────────────────────────────────────────────
# MODE BARU: follow X — pakai akun.txt (authtoken/ct0 per akun, dipisah baris kosong)
# ─────────────────────────────────────────────────────────────────────────────

def load_akun(path="akun.txt"):
    with open(path, encoding="utf-8") as f:
        raw = [l.strip() for l in f]
    pairs, i = [], 0
    while i < len(raw):
        if not raw[i]:
            i += 1
            continue
        auth = raw[i]
        ct0  = raw[i+1] if i+1 < len(raw) else ""
        pairs.append((auth, ct0))
        i += 2
    return pairs


def x_headers(auth_token, ct0):
    return {
        "authorization": f"Bearer {X_BEARER}",
        "cookie": f"auth_token={auth_token}; ct0={ct0}",
        "x-csrf-token": ct0,
        "x-twitter-auth-type": "OAuth2Session",
        "x-twitter-active-user": "yes",
        "x-twitter-client-language": "en",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }


def x_follow(screen_name, auth_token, ct0):
    url = "https://api.twitter.com/1.1/friendships/create.json"
    data = {
        "include_profile_interstitial_type": "1",
        "include_blocking": "1",
        "include_blocked_by": "1",
        "include_followed_by": "1",
        "include_want_retweets": "1",
        "include_mute_edge": "1",
        "include_can_dm": "1",
        "screen_name": screen_name,
    }
    r = requests.post(url, headers=x_headers(auth_token, ct0), data=data, timeout=20)
    return r.status_code, r.text


def run_follow_x(auth_token, ct0, idx):
    print(f"\n{'='*40}")
    print(f"[{idx}] Follow @{TARGET_X_USERNAME}...")
    try:
        status, text = x_follow(TARGET_X_USERNAME, auth_token, ct0)
        if status == 200:
            print("    ✅ Follow sukses")
        elif "already" in text.lower() or "you have already requested" in text.lower():
            print("    ✅ Udah follow sebelumnya")
        elif status == 401:
            print("    ❌ Cookie invalid/expired")
        else:
            print(f"    ⚠ Gagal ({status}): {text[:200]}")
    except Exception as e:
        print(f"    ❌ Error: {e}")


def pick_indices(total, label="akun"):
    print(f"\n┌─────────────────────────────────┐")
    print(f"│     Pilih {label:<22}│")
    print("├─────────────────────────────────┤")
    print("│  1. Satu akun                    │")
    print("│  2. Semua akun                   │")
    print("│  3. Dari akun X sampai akhir      │")
    print("└─────────────────────────────────┘")
    print(f"   Total akun tersedia: {total}")
    choice = input("\nPilih (1/2/3): ").strip()

    if choice == "1":
        n = input(f"\nNomor akun (1–{total}): ").strip()
        try:
            idx = int(n)
            assert 1 <= idx <= total
        except Exception:
            print("❌ Nomor tidak valid")
            return []
        return [idx]
    elif choice == "2":
        return list(range(1, total + 1))
    elif choice == "3":
        n = input(f"Mulai dari akun nomor (1–{total}): ").strip()
        try:
            start = int(n)
            assert 1 <= start <= total
        except Exception:
            print("❌ Nomor tidak valid")
            return []
        return list(range(start, total + 1))
    else:
        print("❌ Pilihan tidak valid")
        return []


async def mode_follow_x():
    akun_pairs = load_akun("akun.txt")
    if not akun_pairs:
        print("❌ akun.txt kosong / gak ketemu")
        return
    total = len(akun_pairs)

    indices = pick_indices(total, label="Akun — Follow X")
    if not indices:
        return

    print(f"\n🚀 Akan follow @{TARGET_X_USERNAME} dari {len(indices)} akun...")
    for pos, idx in enumerate(indices):
        auth_token, ct0 = akun_pairs[idx - 1]
        run_follow_x(auth_token, ct0, idx)
        if pos < len(indices) - 1:
            gap = round(random.uniform(3, 8), 1)
            print(f"\n⏳ Jeda antar akun: {gap}s...")
            await asyncio.sleep(gap)


# ─────────────────────────────────────────────────────────────────────────────

def pick_accounts(sessions, *extra_lists):
    """
    extra_lists: sejumlah list data paralel (x_users, discord_users, dst).
    Hasil tiap item: (idx, sess, *extra_1, *extra_2, ...)
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

    def build(indices):
        return [(i, sessions[i-1], *[lst[i-1] for lst in extra_lists]) for i in indices]

    if choice == "1":
        n = input(f"\nNomor akun (1–{total}): ").strip()
        try:
            idx = int(n)
            if not (1 <= idx <= total):
                raise ValueError
        except ValueError:
            print("❌ Nomor tidak valid")
            return []
        return build([idx])

    elif choice == "2":
        return build(range(1, total+1))

    elif choice == "3":
        n = input(f"Mulai dari akun nomor (1–{total}): ").strip()
        try:
            start = int(n)
            if not (1 <= start <= total):
                raise ValueError
        except ValueError:
            print("❌ Nomor tidak valid")
            return []
        return build(range(start, total+1))

    else:
        print("❌ Pilihan tidak valid")
        return []


async def main():
    sessions = load_file("sessions.txt")

    print("\n┌─────────────────────────────────────┐")
    print("│     LFWallet Bot — Pilih Mode        │")
    print("├─────────────────────────────────────┤")
    print("│  1. Full flow (dari awal)            │")
    print("│  2. Submit USN Discord aja           │")
    print("│  3. Follow X (@LFWallet) — akun.txt  │")
    print("└─────────────────────────────────────┘")
    mode = input("\nPilih mode (1/2/3): ").strip()

    if mode == "1":
        x_users       = load_file("xusn.txt")
        discord_users = load_file("usndc.txt")

        if not (len(sessions) == len(x_users) == len(discord_users)):
            print(f"❌ Jumlah session ({len(sessions)}) ≠ xusn ({len(x_users)}) ≠ usndc ({len(discord_users)})")
            return

        queue = pick_accounts(sessions, x_users, discord_users)
        if not queue:
            return

        print(f"\n🚀 Akan proses {len(queue)} akun...")

        for pos, (idx, sess, xusn, dcusn) in enumerate(queue):
            await run_account(sess, xusn, dcusn, f"ss/{idx}.jpg", idx)
            if pos < len(queue) - 1:
                gap = round(random.uniform(15, 30), 1)
                print(f"\n⏳ Jeda antar akun: {gap}s...")
                await asyncio.sleep(gap)

    elif mode == "2":
        discord_users = load_file("usndc.txt")

        if len(sessions) != len(discord_users):
            print(f"❌ Jumlah session ({len(sessions)}) ≠ usndc ({len(discord_users)})")
            return

        queue = pick_accounts(sessions, discord_users)
        if not queue:
            return

        print(f"\n🚀 Akan proses {len(queue)} akun (mode: Submit USN Discord)...")

        for pos, (idx, sess, dcusn) in enumerate(queue):
            await run_usn_discord_only(sess, dcusn, idx)
            if pos < len(queue) - 1:
                gap = round(random.uniform(15, 30), 1)
                print(f"\n⏳ Jeda antar akun: {gap}s...")
                await asyncio.sleep(gap)

    elif mode == "3":
        await mode_follow_x()

    else:
        print("❌ Mode tidak valid")
        return

    print("\n✅ Semua akun selesai!")


if __name__ == "__main__":
    asyncio.run(main())
