import asyncio
import re
import random
from pyrogram import Client

# ─── CONFIG ───────────────────────────────────────────────
API_ID   = 12345678        # ganti
API_HASH = "your_api_hash" # ganti

BOT      = "AthlediumBiconomyCEXAirdropBot"
REF      = "2005545171"
GROUP    = "Athledium"
# ──────────────────────────────────────────────────────────

def load(path):
    with open(path) as f:
        return [l.strip() for l in f if l.strip()]

def solve(text):
    m = re.search(r'(\d+)\s*([\+\-\*x×÷/])\s*(\d+)', text)
    if not m:
        return None
    a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
    if op == '+':               return a + b
    if op == '-':               return a - b
    if op in ('*', 'x', '×'):  return a * b
    if op in ('/', '÷'):       return a // b

async def wait_bot(app, timeout=5):
    await asyncio.sleep(timeout)
    async for msg in app.get_chat_history(BOT, limit=1):
        return msg
    return None

async def click_btn(msg, keyword):
    if not msg or not msg.reply_markup:
        return False
    for row in msg.reply_markup.inline_keyboard:
        for btn in row:
            if keyword.lower() in btn.text.lower():
                try:
                    await msg.click(btn.text)
                    return True
                except Exception as e:
                    print(f"  ⚠ click '{btn.text}': {e}")
    return False

async def run(session, x_user, wallet, idx):
    print(f"\n[{idx}] ▶ {x_user}")
    app = Client(
        f"sess_{idx}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session
    )

    async with app:
        # 1. START
        await app.send_message(BOT, f"/start {REF}")
        msg = await wait_bot(app, 4)
        print(f"[{idx}] Bot: {(msg.text or '')[:80]}")

        # 2. KLIK CONTINUE
        ok = await click_btn(msg, "continue")
        print(f"[{idx}] Continue → {'✓' if ok else '✗'}")
        msg = await wait_bot(app, 3)

        # 3. JAWAB CAPTCHA (ketik jawaban)
        text = msg.text or msg.caption or ""
        ans  = solve(text)
        if ans is not None:
            await app.send_message(BOT, str(ans))
            print(f"[{idx}] Captcha = {ans} → ✓")
        else:
            print(f"[{idx}] ⚠ Captcha tidak terbaca: {repr(text[:80])}")
        msg = await wait_bot(app, 3)

        # 4. JOIN GROUP
        try:
            await app.join_chat(GROUP)
            print(f"[{idx}] Join group ✓")
        except Exception as e:
            if "already" in str(e).lower():
                print(f"[{idx}] Join group → sudah member, skip")
            else:
                print(f"[{idx}] Join group: {e}")

        # 5. DONE (join)
        ok = await click_btn(msg, "done")
        print(f"[{idx}] Done (join) → {'✓' if ok else '✗'}")
        msg = await wait_bot(app, 3)

        # 6. SUBMIT X USERNAME
        await app.send_message(BOT, x_user)
        print(f"[{idx}] X username: {x_user}")
        msg = await wait_bot(app, 3)

        # 7. DONE (X)
        ok = await click_btn(msg, "done")
        print(f"[{idx}] Done (X) → {'✓' if ok else '✗'}")
        msg = await wait_bot(app, 3)

        # 8. SUBMIT WALLET
        await app.send_message(BOT, wallet)
        print(f"[{idx}] Wallet: {wallet}")
        await asyncio.sleep(3)

        print(f"[{idx}] ✅ Selesai")

async def main():
    sessions  = load("sessions.txt")
    wallets   = load("wallet.txt")
    usernames = load("x_username.txt")

    total = len(sessions)
    print(f"=== Athledium Bot | Total akun: {total} ===")
    print("1. 1 akun")
    print("2. Semua akun")
    print("3. From X to end")
    choice = input("Mode: ").strip()

    if choice == "1":
        n = int(input(f"Nomor akun (1-{total}): ")) - 1
        indices = [n]
    elif choice == "2":
        indices = list(range(total))
    elif choice == "3":
        s = int(input(f"Mulai dari akun ke- (1-{total}): ")) - 1
        indices = list(range(s, total))
    else:
        print("Invalid."); return

    for i in indices:
        try:
            await run(sessions[i], usernames[i], wallets[i], i + 1)
        except Exception as e:
            print(f"[{i+1}] ❌ Error: {e}")
        if i != indices[-1]:
            d = random.randint(8, 20)
            print(f"  ⏳ Delay {d}s...")
            await asyncio.sleep(d)

if __name__ == "__main__":
    asyncio.run(main())
