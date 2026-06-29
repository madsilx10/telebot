import asyncio
from pyrogram import Client

# ===== CONFIG =====
API_ID       = 12345678        # ganti
API_HASH     = 'your_api_hash' # ganti
SESSION_FILE = 'sessions.txt'
WALLET_FILE  = 'wallets.txt'
INTERVAL     = 86400           # 24 jam
TIMEOUT      = 30              # detik nunggu balas bot
# ==================

BOT = '@bnbchain_official_bot'

def load_sessions():
    with open(SESSION_FILE, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def load_wallets():
    with open(WALLET_FILE, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def pilih_akun(wallets):
    print("\n=== BNB FAUCET BOT ===")
    print(f"Total wallet: {len(wallets)}")
    print("1. 1 Akun")
    print("2. Semua Akun")
    print("3. From X to End")
    pilihan = input("\nPilih opsi [1/2/3]: ").strip()

    if pilihan == '1':
        for i, w in enumerate(wallets):
            print(f"{i+1}. {w}")
        idx = int(input("Pilih nomor wallet: ")) - 1
        return [(idx, wallets[idx])]
    elif pilihan == '2':
        return list(enumerate(wallets))
    elif pilihan == '3':
        for i, w in enumerate(wallets):
            print(f"{i+1}. {w}")
        start = int(input("Dari nomor berapa: ")) - 1
        return list(enumerate(wallets))[start:]
    else:
        print("Pilihan tidak valid.")
        exit()

async def tunggu_balas(app, last_id, timeout=TIMEOUT):
    print(f"[*] Nunggu balas bot...")
    for _ in range(timeout):
        await asyncio.sleep(1)
        history = await app.get_chat_history(BOT, limit=1)
        async for msg in history:
            if msg.id > last_id and msg.from_user and msg.from_user.is_bot:
                print(f"[*] Bot balas: {msg.text[:60] if msg.text else '(non-text)'}")
                return msg.id
    print("[!] Timeout, lanjut...")
    return last_id

async def get_last_msg_id(app):
    async for msg in app.get_chat_history(BOT, limit=1):
        return msg.id
    return 0

async def claim(session_string, wallet, akun_ke):
    app = Client(
        f'session_{akun_ke}',
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_string,
        in_memory=True
    )

    async with app:
        print(f"\n[*] Akun {akun_ke+1} | Wallet: {wallet}")

        last_id = await get_last_msg_id(app)

        await app.send_message(BOT, '/start')
        print("[*] /start sent")
        last_id = await tunggu_balas(app, last_id)

        await app.send_message(BOT, 'faucet')
        print("[*] faucet sent")
        last_id = await tunggu_balas(app, last_id)

        await app.send_message(BOT, wallet)
        print(f"[*] Address sent: {wallet}")
        last_id = await tunggu_balas(app, last_id)

        print(f"[+] Done akun {akun_ke+1}")

async def main():
    sessions = load_sessions()
    wallets  = load_wallets()

    if len(sessions) != len(wallets):
        print(f"[!] Jumlah session ({len(sessions)}) dan wallet ({len(wallets)}) beda!")
        exit()

    selected = pilih_akun(wallets)
    print(f"\n[*] Total dipilih: {len(selected)} akun")

    while True:
        for idx, wallet in selected:
            await claim(sessions[idx], wallet, idx)
            await asyncio.sleep(3)

        print(f"\n[*] Semua done. Nunggu {INTERVAL // 3600} jam...\n")
        await asyncio.sleep(INTERVAL)

asyncio.run(main())
