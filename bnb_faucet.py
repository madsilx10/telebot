import asyncio
from pyrogram import Client

# ===== CONFIG =====
API_ID   = 12345678           # ganti dari my.telegram.org
API_HASH = 'your_api_hash'    # ganti
WALLET_FILE = 'wallets.txt'   # file wallet, 1 address per baris
INTERVAL = 86400              # 24 jam dalam detik
# ==================

BOT = '@bnbchain_official_bot'

app = Client('bnb_faucet', api_id=API_ID, api_hash=API_HASH)

def load_wallets():
    with open(WALLET_FILE, 'r') as f:
        wallets = [line.strip() for line in f if line.strip()]
    return wallets

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
        return [wallets[idx]]

    elif pilihan == '2':
        return wallets

    elif pilihan == '3':
        for i, w in enumerate(wallets):
            print(f"{i+1}. {w}")
        start = int(input("Dari nomor berapa: ")) - 1
        return wallets[start:]

    else:
        print("Pilihan tidak valid.")
        exit()

async def claim(wallet):
    print(f"\n[*] Claim untuk: {wallet}")

    await app.send_message(BOT, '/start')
    print("[*] /start sent")
    await asyncio.sleep(4)

    await app.send_message(BOT, 'faucet')
    print("[*] faucet sent")
    await asyncio.sleep(4)

    await app.send_message(BOT, wallet)
    print(f"[+] Done: {wallet}")

async def main():
    wallets = load_wallets()
    selected = pilih_akun(wallets)

    async with app:
        print("\n[*] Connected ke Telegram")

        while True:
            for wallet in selected:
                await claim(wallet)
                await asyncio.sleep(3)

            print(f"\n[*] Semua done. Nunggu {INTERVAL // 3600} jam...\n")
            await asyncio.sleep(INTERVAL)

asyncio.run(main())
