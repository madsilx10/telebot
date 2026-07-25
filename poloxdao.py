import asyncio
import re
import random
from pyrogram import Client

# ─── CONFIG ───────────────────────────────────────────────
API_ID   = 12345678        # ganti
API_HASH = "your_api_hash" # ganti

BOT      = "PoloxDAOAirdropBot"
REF      = "ref_2005545171"
GROUP1   = "poloxdaocommunity"
GROUP2   = "poloxdaoofficial"
USED_YT  = "used_yt.txt"
# ──────────────────────────────────────────────────────────

FIRST = [
    "james","john","robert","michael","william","david","richard","joseph","thomas","charles",
    "oliver","jack","harry","george","noah","leo","oscar","henry","arthur","freddie",
    "emma","sophia","olivia","ava","isabella","mia","charlotte","amelia","harper","evelyn",
    "liam","ethan","mason","logan","lucas","aiden","jackson","sebastian","mateo","jayden",
    "sofia","camila","luna","aria","chloe","penelope","layla","riley","zoey","nora"
]
LAST = [
    "smith","johnson","williams","brown","jones","garcia","miller","davis","wilson","taylor",
    "anderson","thomas","jackson","white","harris","martin","thompson","walker","young","king",
    "scott","green","baker","adams","nelson","carter","mitchell","perez","roberts","turner"
]

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

def load_used():
    try:
        with open(USED_YT) as f:
            return set(l.strip() for l in f if l.strip())
    except FileNotFoundError:
        return set()

def save_used(name):
    with open(USED_YT, "a") as f:
        f.write(name + "\n")

def random_yt():
    used = load_used()
    for _ in range(300):
        fn  = random.choice(FIRST)
        ln  = random.choice(LAST)
        sep = random.choice(["", "_", "."])
        num = random.choice(["", str(random.randint(1, 99))])
        name = fn + sep + ln + num
        if name not in used:
            save_used(name)
            return f"https://www.youtube.com/@{name}"
    raise Exception("Kehabisan nama YouTube unik")

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

async def join(app, chat, idx):
    try:
        await app.join_chat(chat)
        print(f"[{idx}] Join {chat} ✓")
    except Exception as e:
        if "already" in str(e).lower():
            print(f"[{idx}] Join {chat} → sudah member, skip")
        else:
            print(f"[{idx}] Join {chat}: {e}")

async def run(session, email, wallet, idx):
    print(f"\n[{idx}] ▶ {email}")
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
        print(f"[{idx}] Bot: {(msg.text or '')[:100]}")

        # 2. JAWAB CAPTCHA LANGSUNG
        text = msg.text or msg.caption or ""
        ans  = solve(text)
        if ans is not None:
            await app.send_message(BOT, str(ans))
            print(f"[{idx}] Captcha = {ans} ✓")
        else:
            print(f"[{idx}] ⚠ Captcha tidak terbaca: {repr(text[:80])}")
        msg = await wait_bot(app, 3)

        # 3. JOIN GROUP & CHANNEL
        await join(app, GROUP1, idx)
        await join(app, GROUP2, idx)
        await asyncio.sleep(2)

        # 4. KLIK "Submit your details"
        ok = await click_btn(msg, "submit your details")
        print(f"[{idx}] Submit your details → {'✓' if ok else '✗'}")
        msg = await wait_bot(app, 3)

        # 5. SUBMIT EMAIL
        await app.send_message(BOT, email)
        print(f"[{idx}] Email: {email}")
        msg = await wait_bot(app, 3)

        # 6. SUBMIT YOUTUBE LINK (random nama unik)
        yt = random_yt()
        await app.send_message(BOT, yt)
        print(f"[{idx}] YouTube: {yt}")
        msg = await wait_bot(app, 3)

        # 7. KLIK "Done"
        ok = await click_btn(msg, "done")
        print(f"[{idx}] Done → {'✓' if ok else '✗'}")
        msg = await wait_bot(app, 3)

        # 8. KLIK "Yes"
        ok = await click_btn(msg, "yes")
        print(f"[{idx}] Yes → {'✓' if ok else '✗'}")
        msg = await wait_bot(app, 3)

        # 9. SUBMIT WALLET
        await app.send_message(BOT, wallet)
        print(f"[{idx}] Wallet: {wallet}")
        msg = await wait_bot(app, 3)

        # 10. KLIK "Complete the airdrop"
        ok = await click_btn(msg, "complete the airdrop")
        print(f"[{idx}] Complete the airdrop → {'✓' if ok else '✗'}")
        await asyncio.sleep(2)

        print(f"[{idx}] ✅ Selesai")

async def main():
    sessions = load("sessions.txt")
    emails   = load("email.txt")
    wallets  = load("wallet.txt")

    total = len(sessions)
    print(f"=== PoloxDAO Airdrop Bot | Total akun: {total} ===")
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
            await run(sessions[i], emails[i], wallets[i], i + 1)
        except Exception as e:
            print(f"[{i+1}] ❌ Error: {e}")
        if i != indices[-1]:
            d = random.randint(10, 25)
            print(f"  ⏳ Delay {d}s...")
            await asyncio.sleep(d)

if __name__ == "__main__":
    asyncio.run(main())
