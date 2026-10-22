#!/usr/bin/env python3
"""
Elyon Chain Airdrop Bot
Flow: Telegram join group/channel → X follow + like/RT → Submit X username + wallet
Format akun.txt  : auth_token\nct0\n\nauth_token\nct0\n...
Format session.txt: satu session string per baris
"""

import asyncio
import random
import time
import json
import sys
import re
import os
import requests
from pyrogram import Client
from pyrogram.errors import UserAlreadyParticipant, FloodWait, InviteRequestSent

# ─── CONFIG ────────────────────────────────────────────────────────────────────

AKUN_FILE    = "akun.txt"
SESSION_FILE = "session.txt"
WALLET_FILE  = "wallet.txt"  # satu wallet per baris

# Telegram targets
TG_GROUP   = "ELNchain"
TG_CHANNEL = "Elyon_chain"

# X targets
X_FOLLOW_TARGET = "Elyon_Chain"
X_POST_ID       = "2109972690203300093"

COOLDOWN_MIN = 15
COOLDOWN_MAX = 30

API_ID   = 0       # isi API ID Telegram kamu
API_HASH = ""      # isi API Hash Telegram kamu

# ─── LOAD FILES ────────────────────────────────────────────────────────────────

def load_akun(path=AKUN_FILE):
    """Return list of (auth_token, ct0, username|None)"""
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

# ─── X (TWITTER) HELPERS ───────────────────────────────────────────────────────

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

def get_x_username(auth_token, ct0):
    try:
        r = requests.get(
            "https://api.twitter.com/1.1/account/settings.json",
            headers=x_headers(auth_token, ct0),
            timeout=15
        )
        data = r.json()
        return data.get("screen_name")
    except Exception as e:
        print(f"  [!] Gagal ambil username X: {e}")
        return None

def x_follow(auth_token, ct0, target_user):
    try:
        # Ambil user_id target dulu
        r = requests.get(
            f"https://api.twitter.com/1.1/users/show.json?screen_name={target_user}",
            headers=x_headers(auth_token, ct0),
            timeout=15
        )
        user_id = r.json().get("id_str")
        if not user_id:
            print(f"  [!] User ID {target_user} tidak ditemukan")
            return False

        r2 = requests.post(
            "https://api.twitter.com/1.1/friendships/create.json",
            headers=x_headers(auth_token, ct0),
            data={"user_id": user_id, "skip_status": True},
            timeout=15
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
        payload = json.dumps({
            "variables": {"tweet_id": tweet_id},
            "queryId": "lI07N6Otwv1PhnEgXILM7A"
        })
        r = requests.post(
            "https://twitter.com/i/api/graphql/lI07N6Otwv1PhnEgXILM7A/FavoriteTweet",
            headers={**x_headers(auth_token, ct0), "content-type": "application/json"},
            data=payload,
            timeout=15
        )
        data = r.json()
        if "data" in data:
            print(f"  [✓] Like tweet {tweet_id}")
            return True
        print(f"  [!] Like gagal: {data}")
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
            headers={**x_headers(auth_token, ct0), "content-type": "application/json"},
            data=payload,
            timeout=15
        )
        data = r.json()
        if "data" in data:
            print(f"  [✓] Retweet tweet {tweet_id}")
            return True
        print(f"  [!] RT gagal: {data}")
        return False
    except Exception as e:
        print(f"  [!] RT error: {e}")
        return False

# ─── TELEGRAM HELPERS ──────────────────────────────────────────────────────────

async def tg_join(client, target, label):
    try:
        await client.join_chat(target)
        print(f"  [✓] Join {label}: @{target}")
        await asyncio.sleep(random.uniform(2, 4))
    except UserAlreadyParticipant:
        print(f"  [~] Sudah join {label}: @{target}")
    except InviteRequestSent:
        print(f"  [~] Request join terkirim (approval needed): @{target}")
    except FloodWait as e:
        print(f"  [!] FloodWait {e.value}s untuk join @{target}")
        await asyncio.sleep(e.value + 5)
        await tg_join(client, target, label)
    except Exception as e:
        print(f"  [!] Gagal join @{target}: {e}")

# ─── AIRDROP BOT ELYON ─────────────────────────────────────────────────────────

async def run_elyon_airdrop(
    session_string: str,
    auth_token: str,
    ct0: str,
    username: str,
    wallet: str,
    account_index: int,
    start_from_x: bool = False
):
    print(f"\n{'='*55}")
    print(f"[Akun #{account_index+1}] @{username} | Wallet: {wallet[:8]}...")
    print(f"{'='*55}")

    client = Client(
        f"elyon_session_{account_index}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_string,
        in_memory=True
    )

    async with client:
        if not start_from_x:
            # Step 1 – Join Group Telegram
            print(f"[1/6] Join group Telegram...")
            await tg_join(client, TG_GROUP, "Group")
            await asyncio.sleep(random.uniform(1, 3))

            # Step 2 – Join Channel Telegram
            print(f"[2/6] Join channel Telegram...")
            await tg_join(client, TG_CHANNEL, "Channel")
            await asyncio.sleep(random.uniform(1, 3))
        else:
            print(f"[~] Skip Telegram steps (mode 'from X to end')")

    # Step 3 – Follow X
    print(f"[3/6] Follow @{X_FOLLOW_TARGET} di X...")
    x_follow(auth_token, ct0, X_FOLLOW_TARGET)
    await asyncio.sleep(random.uniform(2, 4))

    # Step 4 – Like tweet
    print(f"[4/6] Like tweet...")
    x_like(auth_token, ct0, X_POST_ID)
    await asyncio.sleep(random.uniform(2, 4))

    # Step 5 – Retweet
    print(f"[5/6] Retweet tweet...")
    x_retweet(auth_token, ct0, X_POST_ID)
    await asyncio.sleep(random.uniform(2, 4))

    # Step 6 – Submit ke bot Telegram (simulasi submit usn + wallet)
    # Catatan: jika ada bot Telegram airdrop yang menerima form, submit di sini.
    # Sekarang kita log saja ke file sebagai output akhir.
    print(f"[6/6] Log data submit...")
    with open("elyon_submit_log.txt", "a") as f:
        f.write(f"{username}|{wallet}\n")
    print(f"  [✓] Logged: @{username} | {wallet}")

    print(f"[✓] Akun #{account_index+1} selesai!\n")

# ─── INTERACTIVE MENU ──────────────────────────────────────────────────────────

def menu_pilih_mode():
    print("\n╔══════════════════════════════════╗")
    print("║    ELYON CHAIN AIRDROP BOT       ║")
    print("╠══════════════════════════════════╣")
    print("║  [1] 1 Akun                      ║")
    print("║  [2] Semua Akun                  ║")
    print("║  [3] From X to End (skip TG)     ║")
    print("╚══════════════════════════════════╝")
    pilihan = input("Pilih mode [1/2/3]: ").strip()
    return pilihan

def menu_pilih_akun(total):
    print(f"\nTotal akun: {total}")
    idx = input(f"Pilih akun (1-{total}): ").strip()
    try:
        n = int(idx) - 1
        if 0 <= n < total:
            return n
    except ValueError:
        pass
    print("Input tidak valid.")
    sys.exit(1)

# ─── MAIN ──────────────────────────────────────────────────────────────────────

async def main():
    accounts  = load_akun()
    sessions  = load_sessions()
    wallets   = load_wallets()

    if len(accounts) != len(sessions):
        print(f"[!] Jumlah akun ({len(accounts)}) dan session ({len(sessions)}) tidak sama!")
        sys.exit(1)

    if not API_ID or not API_HASH:
        print("[!] Set API_ID dan API_HASH dulu di bagian CONFIG script ini!")
        sys.exit(1)

    total = len(accounts)

    # Ambil username X tiap akun
    print(f"[*] Fetching {total} username X...")
    for i, acc in enumerate(accounts):
        usn = get_x_username(acc["auth_token"], acc["ct0"])
        accounts[i]["username"] = usn or f"akun_{i+1}"
        print(f"  Akun {i+1}: @{accounts[i]['username']}")
        time.sleep(1)

    pilihan = menu_pilih_mode()

    if pilihan == "1":
        idx = menu_pilih_akun(total)
        indices = [idx]
        start_from_x = False

    elif pilihan == "2":
        indices = list(range(total))
        start_from_x = False

    elif pilihan == "3":
        print(f"\nMode: From X to End (skip join Telegram)")
        idx_input = input(f"Jalankan 1 akun atau semua? (nomor/all): ").strip().lower()
        if idx_input == "all":
            indices = list(range(total))
        else:
            try:
                n = int(idx_input) - 1
                indices = [n] if 0 <= n < total else []
            except ValueError:
                indices = []
        start_from_x = True

    else:
        print("Pilihan tidak valid.")
        sys.exit(1)

    print(f"\n[*] Akan menjalankan {len(indices)} akun...\n")

    for i, idx in enumerate(indices):
        acc     = accounts[idx]
        session = sessions[idx]
        wallet  = wallets[idx] if idx < len(wallets) else "0x0000000000000000000000000000000000000000"

        await run_elyon_airdrop(
            session_string = session,
            auth_token     = acc["auth_token"],
            ct0            = acc["ct0"],
            username       = acc["username"],
            wallet         = wallet,
            account_index  = idx,
            start_from_x   = start_from_x
        )

        if i < len(indices) - 1:
            delay = random.randint(COOLDOWN_MIN, COOLDOWN_MAX)
            print(f"  [~] Cooldown {delay}s sebelum akun berikutnya...")
            await asyncio.sleep(delay)

    print("\n[✓] Semua akun selesai diproses!")
    print("[*] Hasil log: elyon_submit_log.txt")

if __name__ == "__main__":
    asyncio.run(main())
