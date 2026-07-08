import asyncio
import random
import io
import re
from pyrogram import Client
from pyrogram.handlers import MessageHandler
import pytesseract
from PIL import Image

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BOT_USERNAME = "LITHOAirdropBot"
REF_START    = "ref_2005545171"
GROUP        = "lithochat"
CHANNEL      = "Airdrop"

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


def find_keyboard_button(msg, keyword: str) -> str | None:
    try:
        if msg.reply_markup and hasattr(msg.reply_markup, "keyboard"):
            for row in msg.reply_markup.keyboard:
                for btn in row:
                    if keyword.lower() in btn.text.lower():
                        return btn.text
    except Exception:
        pass
    return None


def find_inline_button(msg, keyword: str) -> str | None:
    try:
        if msg.reply_markup and hasattr(msg.reply_markup, "inline_keyboard"):
            for row in msg.reply_markup.inline_keyboard:
                for btn in row:
                    if keyword.lower() in btn.text.lower():
                        return btn.text
    except Exception:
        pass
    return None


async def send_keyboard_button(client, tag: str, msg, keyword: str) -> bool:
    text = find_keyboard_button(msg, keyword)
    if text:
        await client.send_message(BOT_USERNAME, text)
        print(f"{tag} Klik keyboard: '{text}'")
        return True
    print(f"{tag} ⚠️ Keyboard button '{keyword}' tidak ditemukan!")
    return False


async def click_inline_button(tag: str, msg, keyword: str) -> bool:
    text = find_inline_button(msg, keyword)
    if text:
        try:
            await msg.click(text)
            print(f"{tag} Klik inline: '{text}'")
            return True
        except Exception as e:
            print(f"{tag} [Click Error] '{text}' → {e}")
            return False
    print(f"{tag} ⚠️ Inline button '{keyword}' tidak ditemukan!")
    return False


async def ocr_from_message(client: Client, message) -> str:
    try:
        data = await client.download_media(message, in_memory=True)
        img = Image.open(io.BytesIO(data.getvalue()))
        text = pytesseract.image_to_string(img).strip().lower()
        text = re.sub(r"[^a-z]", "", text)
        return text
    except Exception as e:
        print(f"  [OCR Error] {e}")
        return ""


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

            # 1. /start
            await client.send_message(BOT_USERNAME, f"/start {REF_START}")
            msg = await listener.wait()
            print(f"{tag} START: {msg.text or msg.caption or '(no text)'}")

            # 2. Join Airdrop & Register (keyboard button)
            await send_keyboard_button(client, tag, msg, "Join Airdrop")
            msg = await listener.wait()
            print(f"{tag} JOIN: {msg.text or '(no text)'}")

            # 3. Drain sisa pesan bot, simpan pesan terakhir
            try:
                while True:
                    drained = await asyncio.wait_for(listener.queue.get(), timeout=4)
                    msg = drained  # update msg ke pesan terakhir
                    print(f"{tag} DRAIN: {msg.text or '(no text)'}")
            except asyncio.TimeoutError:
                pass

            # 4. Join group & channel
            try:
                await client.join_chat(GROUP)
                print(f"{tag} Joined group: {GROUP}")
            except Exception as e:
                print(f"{tag} Join group skip/error: {e}")

            try:
                await client.join_chat(CHANNEL)
                print(f"{tag} Joined channel: {CHANNEL}")
            except Exception as e:
                print(f"{tag} Join channel skip/error: {e}")

            # 5. Registration (keyboard button, dari msg terakhir)
            await send_keyboard_button(client, tag, msg, "Registration")
            msg = await listener.wait()
            print(f"{tag} REGISTRATION: {msg.text or '(no text)'}")

            # 6. Captcha
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
                await click_inline_button(tag, captcha_msg, emoji_answer)
            else:
                print(f"{tag} ⚠️ Tidak ada mapping untuk '{word}'")

            msg = await listener.wait()

            # 7. Email
            await client.send_message(BOT_USERNAME, email)
            msg = await listener.wait()
            print(f"{tag} Email: {email}")

            # 8. Wallet
            await client.send_message(BOT_USERNAME, wallet)
            msg = await listener.wait()
            print(f"{tag} Wallet: {wallet}")

            # 9. X Profile
            await client.send_message(BOT_USERNAME, x_profile)
            msg = await listener.wait()
            print(f"{tag} X Profile: {x_profile}")

            # 10. Repost
            await client.send_message(BOT_USERNAME, repost)
            msg = await listener.wait()
            print(f"{tag} Repost: {repost}")

            # 11. Yes
            await click_inline_button(tag, msg, "Yes")
            msg = await listener.wait()

            # 12. I Have Joined
            await click_inline_button(tag, msg, "I Have Joined")
            msg = await listener.wait()

            # 13. Joined!
            await click_inline_button(tag, msg, "Joined")
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
    print(f"[1] Pilih 1 akun")
    print(f"[2] Semua akun")
    print(f"[3] Range (dari akun X sampai akhir)")
    opsi = input("Pilih: ").strip()

    if opsi == "1":
        pilihan = input(f"Nomor akun (1-{total}): ").strip()
        try:
            idx = int(pilihan) - 1
            if idx < 0 or idx >= total:
                print(f"Akun tidak valid.")
                return
            indices = [idx]
        except ValueError:
            print("Input tidak valid.")
            return
    elif opsi == "2":
        indices = list(range(total))
    elif opsi == "3":
        pilihan = input(f"Mulai dari akun ke- (1-{total}): ").strip()
        try:
            start = int(pilihan) - 1
            if start < 0 or start >= total:
                print(f"Akun tidak valid.")
                return
            indices = list(range(start, total))
        except ValueError:
            print("Input tidak valid.")
            return
    else:
        print("Pilihan tidak valid.")
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
