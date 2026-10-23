#!/usr/bin/env python3
"""
Elyon Chain Airdrop Bot
Flow: /start reff → soal captcha + klik Continue → jawab captcha
      → join group → join channel → follow X → like + RT
      → klik Done → submit usn X → klik Done → klik Done lagi → submit wallet
Format akun.txt    : auth_token\nct0\n\nauth_token\nct0\n...
Format sessions.txt: satu session string per baris
Format xusn.txt    : satu username X per baris
Format wallet.txt  : satu wallet per baris
"""

import asyncio
import random
import re
import time
import json
import sys
import os
import base64
import requests
from pyrogram import Client
from pyrogram.errors import UserAlreadyParticipant, FloodWait, InviteRequestSent

# ─── CONFIG ────────────────────────────────────────────────────────────────────

AKUN_FILE    = "akun.txt"
SESSION_FILE = "sessions.txt"
WALLET_FILE  = "wallet.txt"
XUSN_FILE    = "xusn.txt"

BOT_USERNAME = "ElyonChainOfficialNewAirdropBot"
REFF_CODE    = "2005545171"
TG_GROUP     = "ELNchain"
TG_CHANNEL   = "Elyon_chain"

X_FOLLOW_TARGET = "Elyon_Chain"
X_POST_ID       = "2109972690203300093"

COOLDOWN_MIN = 15
COOLDOWN_MAX = 30

API_ID   = 0    # isi API ID Telegram kamu
API_HASH = ""   # isi API Hash Telegram kamu

# ─── LOAD FILES ────────────────────────────────────────────────────────────────

def load_akun(path=AKUN_FILE):
    accounts = []
    with open(path) as f:
        lines = [l.strip() for l in f.read().strip().splitlines()]
    i = 0
    while i < len(lines):
        if lines[i] == "":
            i += 1
            continue
        auth_token = lines[i]
        ct0 = lines[i+1] if i+1 < len(lines) else ""
        accounts.append({"auth_token": auth_token, "ct0": ct0, "username": None})
        i += 2
    return accounts

def load_sessions(path=SESSION_FILE):
    with open(path) as f:
        return [l.strip() for l in f if l.strip()]

def load_wallets(path=WALLET_FILE):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [l.strip() for l in f if l.strip()]

def load_xusn(path=XUSN_FILE):
    with open(path) as f:
        return [l.strip() for l in f if l.strip()]

# ─── X HELPERS ─────────────────────────────────────────────────────────────────

def gen_transaction_id():
    return base64.b64encode(os.urandom(75)).decode()

def x_headers(auth_token, ct0):
    return {
        "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
        "cookie": f"auth_token={auth_token}; ct0={ct0}",
        "x-csrf-token": ct0,
        "content-type": "application/json",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "x-twitter-active-user": "yes",
        "x-twitter-auth-type": "OAuth2Session",
        "x-twitter-client-language": "en-US",
        "x-client-transaction-id": gen_transaction_id(),
        "origin": "https://x.com",
        "referer": "https://x.com/",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
    }

def x_get_user_id(auth_token, ct0, screen_name):
    try:
        r = requests.get(
            f"https://twitter.com/i/api/1.1/users/lookup.json?screen_name={screen_name}",
            headers=x_headers(auth_token, ct0),
            timeout=15
        )
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            return data[0]["id_str"]
        print(f"  [!] Gagal ambil user ID {screen_name}: {data}")
        return None
    except Exception as e:
        print(f"  [!] Gagal ambil user ID {screen_name}: {e}")
        return None

def x_follow(auth_token, ct0, target_user):
    try:
        user_id = x_get_user_id(auth_token, ct0, target_user)
        if not user_id:
            return False
        r = requests.post(
            "https://twitter.com/i/api/1.1/friendships/create.json",
            headers={**x_headers(auth_token, ct0), "content-type": "application/x-www-form-urlencoded"},
            data=f"user_id={user_id}&skip_status=true",
            timeout=15
        )
        result = r.json()
        if "id" in result or result.get("following"):
            print(f"  [✓] Follow {target_user}")
            return True
        print(f"  [!] Follow gagal: {result}")
        return False
    except Exception as e:
        print(f"  [!] Follow error: {e}")
        return False

def x_like(auth_token, ct0, tweet_id):
    try:
        payload = json.dumps({
            "variables": {"tweet_id": tweet_id},
            "queryId": "lI07N6Otwv1PhnEgXILM7A"
        })
        r = requests.post(
            "https://twitter.com/i/api/graphql/lI07N6Otwv1PhnEgXILM7A/FavoriteTweet",
            headers=x_headers(auth_token, ct0),
            data=payload,
            timeout=15
        )
        resp = r.json()
        if "data" in resp:
            print(f"  [✓] Like tweet")
            return True
        print(f"  [!] Like gagal: {resp}")
        return False
    except Exception as e:
        print(f"  [!] Like error: {e}")
        return False

def x_retweet(auth_token, ct0, tweet_id):
    try:
        payload = json.dumps({
            "variables": {"tweet_id": tweet_id, "dark_request": False},
            "queryId": "ojPdsZsimiJrUGLR1sjUtA"
        })
        r = requests.post(
            "https://twitter.com/i/api/graphql/ojPdsZsimiJrUGLR1sjUtA/CreateRetweet",
            headers=x_headers(auth_token, ct0),
            data=payload,
            timeout=15
        )
        resp = r.json()
        if "data" in resp:
            print(f"  [✓] Retweet")
            return True
        print(f"  [!] RT gagal: {resp}")
        return False
    except Exception as e:
        print(f"  [!] RT error: {e}")
        return False

# ─── TELEGRAM HELPERS ──────────────────────────────────────────────────────────

async def tg_join(client, target, label):
    try:
        await client.join_chat(target)
        print(f"  [✓] Join {label} {target}")
        await asyncio.sleep(random.uniform(2, 4))
    except UserAlreadyParticipant:
        print(f"  [~] Sudah join {label} {target}")
    except InviteRequestSent:
        print(f"  [~] Request join terkirim: {target}")
    except FloodWait as e:
        print(f"  [!] FloodWait {e.value}s")
        await asyncio.sleep(e.value + 5)
        await tg_join(client, target, label)
    except Exception as e:
        print(f"  [!] Gagal join {target}: {e}")

async def tunggu_pesan_bot(client, bot_id):
    await asyncio.sleep(random.uniform(2, 4))
    async for msg in client.get_chat_history(bot_id, limit=1):
        return msg
    return None

async def klik_button(client, bot_id, msg_id, keyword):
    try:
        msg = await client.get_messages(bot_id, msg_id)
        if not msg.reply_markup:
            print(f"  [!] Tidak ada button")
            return False
        for row in msg.reply_markup.inline_keyboard:
            for btn in row:
                if keyword.lower() in btn.text.lower():
                    await msg.click(btn.text)
                    print(f"  [✓] Klik: {btn.text}")
                    return True
        first = msg.reply_markup.inline_keyboard[0][0]
        await msg.click(first.text)
        print(f"  [~] Fallback klik: {first.text}")
        return True
    except Exception as e:
        print(f"  [!] Klik button error: {e}")
        return False

def solve_captcha(text):
    match = re.search(r'(\d+)\s*([+\-*/x×÷])\s*(\d+)', text)
    if not match:
        return None
    a, op, b = int(match.group(1)), match.group(2), int(match.group(3))
    if op == '+': return a + b
    if op == '-': return a - b
    if op in ('*', 'x', '×'): return a * b
    if op in ('/', '÷'): return a // b if b != 0 else 0
    return None

# ─── FLOW ──────────────────────────────────────────────────────────────────────

async def run_x_only(auth_token, ct0, username, idx):
    print(f"\n{'='*55}")
    print(f"[Akun #{idx+1}] {username} — X Only")
    print(f"{'='*55}")

    print(f"[1] Follow {X_FOLLOW_TARGET}...")
    x_follow(auth_token, ct0, X_FOLLOW_TARGET)
    await asyncio.sleep(random.uniform(2, 3))

    print(f"[2] Like tweet...")
    x_like(auth_token, ct0, X_POST_ID)
    await asyncio.sleep(random.uniform(1, 2))

    print(f"[3] Retweet...")
    x_retweet(auth_token, ct0, X_POST_ID)
    print(f"  [✓] X tasks selesai")

async def run_elyon(session_string, auth_token, ct0, username, wallet, idx):
    print(f"\n{'='*55}")
    print(f"[Akun #{idx+1}] {username} | {wallet[:10]}...")
    print(f"{'='*55}")

    client = Client(
        f"elyon_{idx}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_string,
        in_memory=True
    )

    async with client:
        bot = await client.get_users(BOT_USERNAME)
        bot_id = bot.id

        # [1] Start bot
        print(f"[1] Start bot...")
        await client.send_message(BOT_USERNAME, f"/start {REFF_CODE}")
        await asyncio.sleep(random.uniform(3, 5))

        # [2] Baca soal captcha dari pesan bot, klik Continue
        print(f"[2] Baca soal + klik Continue...")
        msg = await tunggu_pesan_bot(client, bot_id)
        jawaban = None
        if msg and msg.text:
            jawaban = solve_captcha(msg.text)
            if jawaban is not None:
                print(f"  [✓] Soal: {msg.text.strip()} → {jawaban}")
            else:
                print(f"  [!] Gagal parse soal: {msg.text!r}")
            await klik_button(client, bot_id, msg.id, "continue")
        await asyncio.sleep(random.uniform(2, 3))

        # [3] Bot balas → kirim jawaban captcha
        print(f"[3] Jawab captcha...")
        if jawaban is not None:
            await client.send_message(BOT_USERNAME, str(jawaban))
            print(f"  [✓] Jawaban: {jawaban}")
        else:
            print(f"  [!] Skip jawaban")
        await asyncio.sleep(random.uniform(2, 3))

        # [4] Join group
        print(f"[4] Join group {TG_GROUP}...")
        await tg_join(client, TG_GROUP, "Group")
        msg = await tunggu_pesan_bot(client, bot_id)
        if msg and msg.reply_markup:
            await klik_button(client, bot_id, msg.id, "join")
        await asyncio.sleep(random.uniform(2, 3))

        # [5] Join channel
        print(f"[5] Join channel {TG_CHANNEL}...")
        await tg_join(client, TG_CHANNEL, "Channel")
        msg = await tunggu_pesan_bot(client, bot_id)
        if msg and msg.reply_markup:
            await klik_button(client, bot_id, msg.id, "join")
        await asyncio.sleep(random.uniform(2, 3))

        # [6] Follow X
        print(f"[6] Follow {X_FOLLOW_TARGET}...")
        x_follow(auth_token, ct0, X_FOLLOW_TARGET)
        await asyncio.sleep(random.uniform(2, 3))

        # [7] Like + RT
        print(f"[7] Like & RT...")
        x_like(auth_token, ct0, X_POST_ID)
        await asyncio.sleep(random.uniform(1, 2))
        x_retweet(auth_token, ct0, X_POST_ID)
        await asyncio.sleep(random.uniform(2, 3))

        # [8] Klik Done
        print(f"[8] Klik Done...")
        msg = await tunggu_pesan_bot(client, bot_id)
        if msg and msg.reply_markup:
            await klik_button(client, bot_id, msg.id, "done")
        await asyncio.sleep(random.uniform(2, 3))

        # [9] Submit username X
        print(f"[9] Submit username X: {username}...")
        await client.send_message(BOT_USERNAME, username)
        await asyncio.sleep(random.uniform(2, 3))

        # [10] Klik Done
        print(f"[10] Klik Done...")
        msg = await tunggu_pesan_bot(client, bot_id)
        if msg and msg.reply_markup:
            await klik_button(client, bot_id, msg.id, "done")
        await asyncio.sleep(random.uniform(2, 3))

        # [11] Klik Done lagi
        print(f"[11] Klik Done lagi...")
        msg = await tunggu_pesan_bot(client, bot_id)
        if msg and msg.reply_markup:
            await klik_button(client, bot_id, msg.id, "done")
        await asyncio.sleep(random.uniform(2, 3))

        # [12] Submit wallet
        print(f"[12] Submit wallet...")
        await client.send_message(BOT_USERNAME, wallet)
        await asyncio.sleep(random.uniform(1, 2))

    with open("elyon_log.txt", "a") as f:
        f.write(f"{username}|{wallet}\n")
    print(f"  [✓] Selesai!")

# ─── MENU ──────────────────────────────────────────────────────────────────────

def menu(total):
    print("\n╔══════════════════════════════════╗")
    print("║    ELYON CHAIN AIRDROP BOT       ║")
    print("╠══════════════════════════════════╣")
    print("║  [1] 1 Akun                      ║")
    print("║  [2] Semua Akun                  ║")
    print("║  [3] Dari akun X sampai akhir    ║")
    print("╚══════════════════════════════════╝")
    pilihan = input("Pilih [1/2/3]: ").strip()

    if pilihan == "1":
        idx = int(input(f"Nomor akun (1-{total}): ").strip()) - 1
        indices = [idx]
    elif pilihan == "2":
        indices = list(range(total))
    elif pilihan == "3":
        mulai = int(input(f"Mulai dari akun ke- (1-{total}): ").strip()) - 1
        indices = list(range(mulai, total))
    else:
        print("Pilihan tidak valid.")
        sys.exit(1)

    print("\n╔══════════════════════════════════╗")
    print("║  [1] Full                        ║")
    print("║  [2] X Only (follow, like, RT)   ║")
    print("╚══════════════════════════════════╝")
    mode = input("Pilih mode [1/2]: ").strip()

    if mode == "1":
        x_only = False
    elif mode == "2":
        x_only = True
    else:
        print("Pilihan tidak valid.")
        sys.exit(1)

    return indices, x_only

# ─── MAIN ──────────────────────────────────────────────────────────────────────

async def main():
    if not API_ID or not API_HASH:
        print("[!] Set API_ID dan API_HASH dulu!")
        sys.exit(1)

    accounts = load_akun()
    sessions = load_sessions()
    wallets  = load_wallets()
    xusns    = load_xusn()

    if not (len(accounts) == len(sessions) == len(xusns)):
        print(f"[!] Jumlah tidak sama — akun: {len(accounts)}, sessions: {len(sessions)}, xusn: {len(xusns)}")
        sys.exit(1)

    total = len(accounts)
    for i, usn in enumerate(xusns):
        accounts[i]["username"] = usn
        print(f"  [{i+1}] {usn}")

    indices, x_only = menu(total)
    print(f"\n[*] Menjalankan {len(indices)} akun...\n")

    for i, idx in enumerate(indices):
        acc    = accounts[idx]
        wallet = wallets[idx] if idx < len(wallets) else "0x000000000000000000000000000000000000dEaD"

        if x_only:
            await run_x_only(
                auth_token = acc["auth_token"],
                ct0        = acc["ct0"],
                username   = acc["username"],
                idx        = idx,
            )
        else:
            await run_elyon(
                session_string = sessions[idx],
                auth_token     = acc["auth_token"],
                ct0            = acc["ct0"],
                username       = acc["username"],
                wallet         = wallet,
                idx            = idx,
            )

        if i < len(indices) - 1:
            delay = random.randint(COOLDOWN_MIN, COOLDOWN_MAX)
            print(f"\n[~] Cooldown {delay}s...\n")
            await asyncio.sleep(delay)

    print("\n[✓] Semua akun selesai!")
    print("[*] Log: elyon_log.txt")

if __name__ == "__main__":
    asyncio.run(main())
