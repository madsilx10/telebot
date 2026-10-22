#!/usr/bin/env python3
"""
Elyon Chain Airdrop Bot
Flow: Start bot (reff) → klik Continue → join group → join channel
      → follow X → like+RT → klik Done → submit usn X → submit wallet → Done
Format akun.txt   : auth_token\nct0\n\nauth_token\nct0\n...
Format sessions.txt: satu session string per baris
Format wallet.txt  : satu wallet per baris
"""

import asyncio
import random
import time
import json
import sys
import os
import requests
from pyrogram import Client
from pyrogram.errors import UserAlreadyParticipant, FloodWait, InviteRequestSent

# ─── CONFIG ────────────────────────────────────────────────────────────────────

AKUN_FILE    = "akun.txt"
SESSION_FILE = "sessions.txt"
WALLET_FILE  = "wallet.txt"
XUSN_FILE    = "xusn.txt"

BOT_USERNAME  = "ElyonChainOfficialNewAirdropBot"
REFF_CODE     = "2005545171"
TG_GROUP      = "ELNchain"
TG_CHANNEL    = "Elyon_chain"

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

def x_headers(auth_token, ct0):
    return {
        "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I7wHZn%2FxXNo%3DLiMQJEMbEMfYMVqB6N0bN2WNBO8KvIW",
        "cookie": f"auth_token={auth_token}; ct0={ct0}",
        "x-csrf-token": ct0,
        "content-type": "application/json",
        "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36",
        "x-twitter-active-user": "yes",
        "x-twitter-auth-type": "OAuth2Session",
        "x-twitter-client-language": "en",
    }


def x_follow(auth_token, ct0, target_user):
    try:
        r = requests.get(
            f"https://api.twitter.com/1.1/users/show.json?screen_name={target_user}",
            headers=x_headers(auth_token, ct0), timeout=15
        )
        user_id = r.json().get("id_str")
        if not user_id:
            print(f"  [!] User ID @{target_user} tidak ditemukan")
            return False
        r2 = requests.post(
            "https://api.twitter.com/1.1/friendships/create.json",
            headers=x_headers(auth_token, ct0),
            data={"user_id": user_id, "skip_status": True}, timeout=15
        )
        result = r2.json()
        if "id" in result or result.get("following"):
            print(f"  [✓] Follow @{target_user}")
            return True
        print(f"  [!] Follow gagal: {result}")
        return False
    except Exception as e:
        print(f"  [!] Follow error: {e}")
        return False

def x_like(auth_token, ct0, tweet_id):
    try:
        r = requests.post(
            "https://twitter.com/i/api/graphql/lI07N6Otwv1PhnEgXILM7A/FavoriteTweet",
            headers=x_headers(auth_token, ct0),
            data=json.dumps({"variables": {"tweet_id": tweet_id}, "queryId": "lI07N6Otwv1PhnEgXILM7A"}),
            timeout=15
        )
        if "data" in r.json():
            print(f"  [✓] Like tweet")
            return True
        print(f"  [!] Like gagal: {r.json()}")
        return False
    except Exception as e:
        print(f"  [!] Like error: {e}")
        return False

def x_retweet(auth_token, ct0, tweet_id):
    try:
        r = requests.post(
            "https://twitter.com/i/api/graphql/ojPdsZsimiJrUGLR1sjUtA/CreateRetweet",
            headers=x_headers(auth_token, ct0),
            data=json.dumps({"variables": {"tweet_id": tweet_id, "dark_request": False}, "queryId": "ojPdsZsimiJrUGLR1sjUtA"}),
            timeout=15
        )
        if "data" in r.json():
            print(f"  [✓] Retweet")
            return True
        print(f"  [!] RT gagal: {r.json()}")
        return False
    except Exception as e:
        print(f"  [!] RT error: {e}")
        return False

# ─── TELEGRAM HELPERS ──────────────────────────────────────────────────────────

async def tg_join(client, target, label):
    try:
        await client.join_chat(target)
        print(f"  [✓] Join {label} @{target}")
        await asyncio.sleep(random.uniform(2, 4))
    except UserAlreadyParticipant:
        print(f"  [~] Sudah join {label} @{target}")
    except InviteRequestSent:
        print(f"  [~] Request join terkirim: @{target}")
    except FloodWait as e:
        print(f"  [!] FloodWait {e.value}s")
        await asyncio.sleep(e.value + 5)
        await tg_join(client, target, label)
    except Exception as e:
        print(f"  [!] Gagal join @{target}: {e}")

async def klik_button(client, chat_id, message_id, keyword):
    """Klik inline button yang teksnya mengandung keyword (case-insensitive)"""
    try:
        msg = await client.get_messages(chat_id, message_id)
        if not msg.reply_markup:
            print(f"  [!] Tidak ada button di pesan")
            return False
        for row in msg.reply_markup.inline_keyboard:
            for btn in row:
                if keyword.lower() in btn.text.lower():
                    await msg.click(btn.text)
                    print(f"  [✓] Klik button: {btn.text}")
                    return True
        # Kalau keyword ga match, klik button pertama yang ada
        first_btn = msg.reply_markup.inline_keyboard[0][0]
        await msg.click(first_btn.text)
        print(f"  [~] Fallback klik button pertama: {first_btn.text}")
        return True
    except Exception as e:
        print(f"  [!] Klik button error: {e}")
        return False

async def tunggu_pesan_bot(client, bot_id, timeout=20):
    """Tunggu pesan terbaru dari bot"""
    await asyncio.sleep(random.uniform(2, 4))
    msgs = []
    async for msg in client.get_chat_history(bot_id, limit=1):
        msgs.append(msg)
    return msgs[0] if msgs else None

# ─── MAIN FLOW ─────────────────────────────────────────────────────────────────

async def run_elyon(session_string, auth_token, ct0, username, wallet, idx, start_from_x=False):
    print(f"\n{'='*55}")
    print(f"[Akun #{idx+1}] @{username} | {wallet[:10]}...")
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

        if not start_from_x:
            # Step 1 – /start dengan reff
            print(f"[1] Start bot dengan reff...")
            await client.send_message(BOT_USERNAME, f"/start {REFF_CODE}")
            await asyncio.sleep(random.uniform(3, 5))

            # Step 2 – Klik Continue / jawab captcha
            print(f"[2] Klik Continue...")
            msg = await tunggu_pesan_bot(client, bot_id)
            if msg:
                await klik_button(client, bot_id, msg.id, "continue")
            await asyncio.sleep(random.uniform(2, 3))

            # Step 3 – Join group
            print(f"[3] Join group @{TG_GROUP}...")
            await tg_join(client, TG_GROUP, "Group")
            msg = await tunggu_pesan_bot(client, bot_id)
            if msg and msg.reply_markup:
                await klik_button(client, bot_id, msg.id, "join")
            await asyncio.sleep(random.uniform(2, 3))

            # Step 4 – Join channel
            print(f"[4] Join channel @{TG_CHANNEL}...")
            await tg_join(client, TG_CHANNEL, "Channel")
            msg = await tunggu_pesan_bot(client, bot_id)
            if msg and msg.reply_markup:
                await klik_button(client, bot_id, msg.id, "join")
            await asyncio.sleep(random.uniform(2, 3))

        else:
            print(f"[~] Skip Telegram steps")

        # Step 5 – Follow X
        print(f"[5] Follow @{X_FOLLOW_TARGET}...")
        x_follow(auth_token, ct0, X_FOLLOW_TARGET)
        await asyncio.sleep(random.uniform(2, 3))

        # Step 6 – Like + RT
        print(f"[6] Like & RT tweet...")
        x_like(auth_token, ct0, X_POST_ID)
        await asyncio.sleep(random.uniform(1, 2))
        x_retweet(auth_token, ct0, X_POST_ID)
        await asyncio.sleep(random.uniform(2, 3))

        # Step 7 – Klik Done (setelah X tasks)
        print(f"[7] Klik Done...")
        msg = await tunggu_pesan_bot(client, bot_id)
        if msg and msg.reply_markup:
            await klik_button(client, bot_id, msg.id, "done")
        await asyncio.sleep(random.uniform(2, 3))

        # Step 8 – Submit username X
        print(f"[8] Submit username X: @{username}...")
        await client.send_message(BOT_USERNAME, username)
        await asyncio.sleep(random.uniform(2, 3))

        # Step 9 – Klik Done setelah submit usn
        print(f"[9] Klik Done (konfirmasi usn)...")
        msg = await tunggu_pesan_bot(client, bot_id)
        if msg and msg.reply_markup:
            await klik_button(client, bot_id, msg.id, "done")
        await asyncio.sleep(random.uniform(2, 3))

        # Step 10 – Submit wallet address
        print(f"[10] Submit wallet: {wallet}...")
        await client.send_message(BOT_USERNAME, wallet)
        await asyncio.sleep(random.uniform(2, 3))

        # Step 11 – Klik Done terakhir
        print(f"[11] Klik Done (konfirmasi wallet)...")
        msg = await tunggu_pesan_bot(client, bot_id)
        if msg and msg.reply_markup:
            await klik_button(client, bot_id, msg.id, "done")
        await asyncio.sleep(random.uniform(1, 2))

    # Log hasil
    with open("elyon_log.txt", "a") as f:
        f.write(f"{username}|{wallet}\n")
    print(f"  [✓] Selesai! Logged ke elyon_log.txt")

# ─── MENU ──────────────────────────────────────────────────────────────────────

def menu():
    print("\n╔══════════════════════════════════╗")
    print("║    ELYON CHAIN AIRDROP BOT       ║")
    print("╠══════════════════════════════════╣")
    print("║  [1] 1 Akun                      ║")
    print("║  [2] Semua Akun                  ║")
    print("║  [3] From X to End (skip TG)     ║")
    print("╚══════════════════════════════════╝")
    return input("Pilih mode [1/2/3]: ").strip()

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
        print(f"  [{i+1}] @{usn}")

    pilihan = menu()
    start_from_x = False

    if pilihan == "1":
        idx = int(input(f"Pilih akun (1-{total}): ").strip()) - 1
        indices = [idx]

    elif pilihan == "2":
        indices = list(range(total))

    elif pilihan == "3":
        start_from_x = True
        inp = input(f"Nomor akun atau 'all': ").strip().lower()
        indices = list(range(total)) if inp == "all" else [int(inp)-1]

    else:
        print("Pilihan tidak valid.")
        sys.exit(1)

    print(f"\n[*] Menjalankan {len(indices)} akun...\n")

    for i, idx in enumerate(indices):
        acc    = accounts[idx]
        wallet = wallets[idx] if idx < len(wallets) else "0x000000000000000000000000000000000000dEaD"

        await run_elyon(
            session_string = sessions[idx],
            auth_token     = acc["auth_token"],
            ct0            = acc["ct0"],
            username       = acc["username"],
            wallet         = wallet,
            idx            = idx,
            start_from_x   = start_from_x
        )

        if i < len(indices) - 1:
            delay = random.randint(COOLDOWN_MIN, COOLDOWN_MAX)
            print(f"\n[~] Cooldown {delay}s...\n")
            await asyncio.sleep(delay)

    print("\n[✓] Semua akun selesai!")
    print("[*] Log: elyon_log.txt")

if __name__ == "__main__":
    asyncio.run(main())
