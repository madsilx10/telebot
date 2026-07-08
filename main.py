import asyncio
import random
import io
import re
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
import pytesseract
from PIL import Image

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BOT_USERNAME = "LITHOAirdropBot"
REF_START    = "ref_2005545171"
GROUP        = "lithochat"
CHANNEL      = "Airdrop"

# Word → Emoji mapping (isi setelah spy)
WORD_EMOJI_MAP = {
    "laptop":     "💻",
    "glove":      "🧤",
    "sword":      "⚔️",
    "flashlight": "🔦",
    "ladder":     "🪜",
    "sock":       "🧦",
    "mirror":     "🪞",
    "axe":        "🪓",
    "mailbox":    "📫",
}
# ──────────────────────────────────────────────────────────────────────────────


def load_file(path):
    with open(path, "r") as f:
        return [line.strip() for line in f if line.strip()]


def generate_repost(x_profile: str) -> str:
    username = x_profile.rstrip("/").split("/")[-1]
    rand = "".join([str(random.randint(0, 9)) for _ in range(17)])
    return f"https://x.com/{username}/status/20{rand}"


async def ocr_from_message(client: Client, message) -> str:
    try:
        data = await client.download_media(message, in_memory=True)
        img = Image.open(io.BytesIO(data.getbuffer()))
        text = pytesseract.image_to_string(img).strip().lower()
        text = re.sub(r"[^a-z]", "", text)
        return text
    except Exception as e:
        print(f"  [OCR Error] {e}")
        return ""


async def click_button(message, label: str) -> bool:
    if not message.reply_markup:
        return False
    try:
        await message.click(label)
        return True
    except Exception as e:
        print(f"  [Click Error] label='{label}' → {e}")
        return False


class BotListener:
    def __init__(self, client: Client, bot_username: str):
        self.client = client
        self.bot_username = bot_username.lower()
        self.queue: asyncio.Queue = asyncio.Queue()
        self._handler = None

    async def start(self):
        async def _on_msg(c, m):
            if m.chat and m.chat.username and \
               m.chat.username.lower() == self.bot_username:
                await self.queue.put(m)
        self._handler = MessageHandler(_on_msg)
        self.client.add_handler(self._handler)

    def stop(self):
        if self._handler:
            self.client.remove_handler(self._handler)

    async def wait(self, timeout=60):
        return await asyncio.wait_for(self.queue.get(), timeout=timeout)


async def run_account(session_string: str, email: str, x_profile: str, wallet: str, index: int):
    tag = f"[Akun-{index+1}]"
    repost = generate_repost(x_profile)

    client = Client(
        name=f"session_{index}",
        session_string=session_string,
        no_updates=False,
        in_memory=True,
    )

    async with client:
        listener = BotListener(client, BOT_USERNAME)
        await listener.start()

        try:
            print(f"{tag} Memulai...")

            # 1. /start dengan referral
            await client.send_message(BOT_USERNAME, f"/start {REF_START}")
            msg = await listener.wait()
            print(f"{tag} START: {msg.text or msg.caption or '(no text)'}")
            await asyncio.sleep(2)

            # 2. Klik 'Join Airdrop & Register'
            await client.send_message(BOT_USERNAME, "💻 Join Airdrop & Register")
            msg = await listener.wait()
            await asyncio.sleep(2)

            # 3. Drain pesan bot (join group/channel info)
            try:
                while True:
                    msg = await asyncio.wait_for(listener.queue.get(), timeout=3)
            except asyncio.TimeoutError:
                pass
            await asyncio.sleep(2)

            # 4. Registration
            await client.send_message(BOT_USERNAME, "📝 Registration")  # cek spy kalau salah
            msg = await listener.wait()
            print(f"{tag} REGISTRATION: {msg.text or '(no text)'}")
            await asyncio.sleep(2)

            # 5. Captcha
            captcha_msg = msg
            if not captcha_msg.photo:
                captcha_msg = await listener.wait()

            word = await ocr_from_message(client, captcha_msg)
            print(f"{tag} OCR: '{word}'")

            emoji_answer = None
            for key, emoji in WORD_EMOJI_MAP.items():
                if key in word:
                    emoji_answer = emoji
                    break

            if emoji_answer:
                clicked = await click_button(captcha_msg, emoji_answer)
                print(f"{tag} Captcha klik: {emoji_answer} → {'ok' if clicked else 'gagal'}")
            else:
                print(f"{tag} ⚠️ Tidak ada mapping untuk '{word}'")

            msg = await listener.wait()
            await asyncio.sleep(2)

            # 6. Email
            await client.send_message(BOT_USERNAME, email)
            msg = await listener.wait()
            print(f"{tag} Email: {email}")
            await asyncio.sleep(2)

            # 7. Wallet
            await client.send_message(BOT_USERNAME, wallet)
            msg = await listener.wait()
            print(f"{tag} Wallet: {wallet}")
            await asyncio.sleep(2)

            # 8. X Profile
            await client.send_message(BOT_USERNAME, x_profile)
            msg = await listener.wait()
            print(f"{tag} X Profile: {x_profile}")
            await asyncio.sleep(2)

            # 9. Repost
            await client.send_message(BOT_USERNAME, repost)
            msg = await listener.wait()
            print(f"{tag} Repost: {repost}")
            await asyncio.sleep(2)

            # 10. Yes
            await click_button(msg, "✅ Yes")
            msg = await listener.wait()
            await asyncio.sleep(2)

            # 11. I Have Joined
            await click_button(msg, "✅ I Have Joined")
            msg = await listener.wait()
            await asyncio.sleep(2)

            # 12. Joined!
            await click_button(msg, "🎉 Joined!")
            msg = await listener.wait(timeout=30)
            print(f"{tag} ✅ SELESAI! {msg.text or '(no text)'}")

        except asyncio.TimeoutError:
            print(f"{tag} ⚠️ Timeout nunggu respons bot")
        except Exception as e:
            print(f"{tag} ❌ Error: {e}")
        finally:
            listener.stop()


async def main():
    sessions   = load_file("sessions.txt")
    emails     = load_file("email.txt")
    x_profiles = load_file("x_profile.txt")
    wallets    = load_file("wallet.txt")

    total = len(sessions)
    print(f"Total akun: {total}")
    pilihan = input(f"Pilih akun (1-{total}): ").strip()

    try:
        idx = int(pilihan) - 1
        if idx < 0 or idx >= total:
            print(f"Akun tidak valid. Harus antara 1-{total}")
            return
        indices = [idx]
    except ValueError:
        print("Input tidak valid.")
        return

    tasks = []
    for i in indices:
        email     = emails[i % len(emails)]
        x_profile = x_profiles[i % len(x_profiles)]
        wallet    = wallets[i % len(wallets)]
        tasks.append(run_account(sessions[i], email, x_profile, wallet, i))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
