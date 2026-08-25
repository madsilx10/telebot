import asyncio, random, re, os, json, secrets
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from pyrogram.raw import functions
from urllib.parse import urlparse, parse_qs, unquote
import httpx
from curl_cffi.requests import AsyncSession

# ─── Config ────────────────────────────────────────────────────────────────
def load(f): return open(f).read().splitlines()

sessions  = load("sessions.txt")
profiles  = load("x_profile.txt")
emails    = load("email.txt")
wallets   = load("wallet.txt")
apikeys   = load("apikey.txt")

# akun.txt: blok per akun, tiap blok 2 baris → auth_token / ct0
def load_twitter_creds():
    raw = open("akun.txt").read().strip().split("\n\n")
    result = []
    for block in raw:
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        if len(lines) >= 2:
            result.append({"auth_token": lines[0], "ct0": lines[1]})
    return result

twitter_creds = load_twitter_creds()

API_ID   = 123456
API_HASH = "your_api_hash"

BOT            = "PaygentAirdropBot"
START          = "ref_2005545171"
FOLLOW_TARGET  = "Paygent_"          # ← ganti kalau beda
SAFEGUARD_BOT  = "safeguard"
PAYGENTUSE_CH  = "paygentuse"

followed     = set(open("followed.txt").read().splitlines()) if os.path.exists("followed.txt") else set()
joined       = set(open("joined.txt").read().splitlines())   if os.path.exists("joined.txt")   else set()

# ─── Helpers ────────────────────────────────────────────────────────────────
def log(idx, msg):
    print(f"  [{idx:>3}] {msg}")

def mark_followed(idx):
    followed.add(str(idx))
    with open("followed.txt", "a") as f:
        f.write(f"{idx}\n")

def mark_joined(idx):
    joined.add(str(idx))
    with open("joined.txt", "a") as f:
        f.write(f"{idx}\n")

def gen_repost(profile_url):
    uname = profile_url.rstrip("/").split("/")[-1]
    sid   = random.randint(1000000000000000000, 9999999999999999999)
    return f"https://x.com/{uname}/status/{sid}?s=20"

def solve_math(text):
    m = re.search(r'(\d+)\s*([+\-*/])\s*(\d+)', text or "")
    return str(eval(f"{m[1]}{m[2]}{m[3]}")) if m else None

# ─── Twitter: follow ────────────────────────────────────────────────────────
def x_headers(auth_token: str, ct0: str) -> dict:
    return {
        "cookie":                    f"auth_token={auth_token}; ct0={ct0}",
        "x-csrf-token":              ct0,
        "authorization":             "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
        "user-agent":                "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "accept":                    "*/*",
        "accept-encoding":           "gzip, deflate, br",
        "accept-language":           "en-US,en;q=0.9",
        "x-twitter-active-user":     "yes",
        "x-twitter-auth-type":       "OAuth2Session",
        "x-twitter-client-language": "en",
        "x-client-transaction-id":   secrets.token_urlsafe(96),
        "content-type":              "application/x-www-form-urlencoded",
        "origin":                    "https://x.com",
        "referer":                   f"https://x.com/{FOLLOW_TARGET}",
        "sec-ch-ua":                 '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile":          "?1",
        "sec-ch-ua-platform":        '"Android"',
        "sec-fetch-dest":            "empty",
        "sec-fetch-mode":            "cors",
        "sec-fetch-site":            "same-origin",
    }

async def get_target_user_id(auth_token: str, ct0: str) -> str:
    from urllib.parse import urlencode
    variables = json.dumps({"screen_name": FOLLOW_TARGET, "withGrokTranslatedBio": True})
    features  = json.dumps({
        "hidden_profile_subscriptions_enabled": True,
        "profile_label_improvements_pcf_label_in_post_enabled": True,
        "responsive_web_profile_redirect_enabled": False,
        "rweb_tipjar_consumption_enabled": False,
        "verified_phone_label_enabled": False,
        "subscriptions_verification_info_is_identity_verified_enabled": True,
        "subscriptions_verification_info_verified_since_enabled": True,
        "highlights_tweets_tab_ui_enabled": True,
        "responsive_web_twitter_article_notes_tab_enabled": True,
        "subscriptions_feature_can_gift_premium": True,
        "creator_subscriptions_tweet_preview_api_enabled": True,
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
        "responsive_web_graphql_timeline_navigation_enabled": True,
    })
    field_toggles = json.dumps({"withAuxiliaryUserLabels": True})
    params = urlencode({"variables": variables, "features": features, "fieldToggles": field_toggles})
    url    = f"https://x.com/i/api/graphql/2qvSHpkWTMS9i0zJAwDNiA/UserByScreenName?{params}"
    async with AsyncSession(impersonate="chrome124") as s:
        r = await s.get(url, headers=x_headers(auth_token, ct0))
    data = r.json()
    uid  = data.get("data", {}).get("user", {}).get("result", {}).get("rest_id")
    if not uid:
        raise Exception(f"Gagal lookup @{FOLLOW_TARGET}: {str(data)[:200]}")
    return uid

async def twitter_follow(auth_token: str, ct0: str, idx: int):
    target_id = await get_target_user_id(auth_token, ct0)
    log(idx, f"[Twitter] @{FOLLOW_TARGET} id={target_id}")
    async with AsyncSession(impersonate="chrome124") as s:
        r = await s.post(
            f"https://x.com/i/api/1.1/friendships/create.json?user_id={target_id}",
            headers=x_headers(auth_token, ct0),
        )
    log(idx, f"[Twitter follow] status={r.status_code} body={r.text[:150]}")
    if r.status_code == 403:
        log(idx, "[Twitter] Sudah follow (403), skip.")
        return
    if r.status_code == 401:
        raise Exception("Twitter follow 401 — token mati.")
    data = r.json()
    if data.get("errors"):
        err = data["errors"][0]
        if err.get("code") == 160:
            log(idx, "[Twitter] Sudah request follow (protected), skip.")
            return
        raise Exception(f"Twitter follow error [{err.get('code')}]: {err.get('message')}")
    log(idx, "[Twitter] Follow OK ✓")

# ─── Bot Interaction ─────────────────────────────────────────────────────────
async def click_btn(app, msg, keyword=None):
    for row in (msg.reply_markup.inline_keyboard if msg.reply_markup and hasattr(msg.reply_markup, "inline_keyboard") else []):
        for btn in row:
            if not btn.callback_data: continue
            cb = btn.callback_data
            if keyword and keyword.lower() not in cb.lower(): continue
            await app.invoke(functions.messages.GetBotCallbackAnswer(
                peer=await app.resolve_peer(BOT),
                msg_id=msg.id,
                data=cb.encode()
            ))
            return True
    return False

async def bypass_safeguard(app, msg, bot_username=None):
    """Generic safeguard bypass — works for PaygentBot flow & @paygentuse flow."""
    # Cari button yang punya web_app atau url safeguard (jangan hardcode [0][0])
    btn = None
    url = None
    for row in (msg.reply_markup.inline_keyboard if msg.reply_markup and hasattr(msg.reply_markup, "inline_keyboard") else []):
        for b in row:
            if hasattr(b, "web_app") and b.web_app:
                btn = b
                url = b.web_app.url
                break
            if b.url and "safeguard" in b.url:
                btn = b
                url = b.url
                break
        if btn:
            break
    if not btn or not url:
        raise Exception(f"Safeguard button tidak ditemukan di pesan (chat={msg.chat.id} msg_id={msg.id})")
    p   = parse_qs(urlparse(url).query)
    me  = await app.get_me()

    if bot_username:
        bot_peer = await app.resolve_peer(bot_username)
    elif msg.from_user:
        bot_peer = await app.resolve_peer(msg.from_user.id)
    else:
        bot_peer = await app.resolve_peer(BOT)

    res = await app.invoke(functions.messages.RequestSimpleWebView(
        bot=bot_peer,
        url=url,
        platform="android",
    ))
    init_data = unquote(urlparse(res.url).fragment.split("tgWebAppData=")[1].split("&")[0])

    async with httpx.AsyncClient() as s:
        r = await s.post("https://www.safeguard.run/api/verify", json={
            "token": True, "tglogin": init_data,
            "request_query": {
                "chat_id":        p["chat_id"][0],
                "msg_id":         int(p["msg_id"][0]),
                "hash":           p["hash"][0],
                "portal":         p.get("portal", ["yes"])[0],
                "signature":      p["signature"][0],
                "timestamp":      int(p["timestamp"][0]),
                "user_id":        me.id,
                "user_firstname": me.first_name,
                "username":       me.username,
            }
        }, headers={
            "Origin":  "https://www.safeguard.run",
            "Referer": f"https://www.safeguard.run/?hash={p.get('hash', [''])[0]}",
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
        })
        return r.json()

async def wait_msg(app, chat=None, timeout=30):
    """Tunggu pesan masuk dari chat tertentu (default: BOT)."""
    target = chat or BOT
    loop   = asyncio.get_running_loop()
    future = loop.create_future()

    async def _handler(client, message):
        if not future.done():
            future.set_result(message)

    handler, group = app.add_handler(
        MessageHandler(_handler, filters.chat(target) & filters.incoming)
    )
    try:
        return await asyncio.wait_for(future, timeout=timeout)
    except asyncio.TimeoutError:
        async for msg in app.get_chat_history(target, limit=1):
            return msg
    finally:
        app.remove_handler(handler, group)

# ─── Join Group via @paygentuse ──────────────────────────────────────────────
async def join_group_via_paygentuse(app, idx):
    """
    Flow:
    1. Baca pesan channel @paygentuse → cari button web_app (Tap to verify)
    2. bypass_safeguard() → POST /api/verify
    3. Safeguard kirim invite link ke user via @safeguard bot
    4. Join chat via link itu
    """
    # 1. Cari pesan dengan web_app button di @paygentuse
    target_msg = None
    async for msg in app.get_chat_history(PAYGENTUSE_CH, limit=20):
        if not (msg.reply_markup and hasattr(msg.reply_markup, "inline_keyboard")):
            continue
        for row in msg.reply_markup.inline_keyboard:
            for btn in row:
                has_webapp = hasattr(btn, "web_app") and btn.web_app
                has_sg_url = btn.url and "safeguard" in (btn.url or "")
                if has_webapp or has_sg_url:
                    target_msg = msg
                    break
            if target_msg:
                break

    if not target_msg:
        # Debug: print semua pesan & button yang ada
        log(idx, "[Join DEBUG] Tidak ketemu, dump semua pesan @paygentuse:")
        async for msg in app.get_chat_history(PAYGENTUSE_CH, limit=5):
            log(idx, f"  msg_id={msg.id} text={repr((msg.text or '')[:60])}")
            if msg.reply_markup and hasattr(msg.reply_markup, "inline_keyboard"):
                for ri, row in enumerate(msg.reply_markup.inline_keyboard):
                    for bi, b in enumerate(row):
                        log(idx, f"    btn[{ri}][{bi}] text={repr(getattr(b,'text',''))} cb={getattr(b,'callback_data',None)} url={getattr(b,'url',None)} web_app={getattr(b,'web_app',None)}")
            else:
                log(idx, "    (no inline keyboard)")
        raise Exception("Pesan 'Tap to verify' di @paygentuse tidak ditemukan")

    log(idx, f"[Join] Ketemu pesan @paygentuse msg_id={target_msg.id}")
    # Debug button yang kepilih
    for ri, row in enumerate(target_msg.reply_markup.inline_keyboard):
        for bi, b in enumerate(row):
            log(idx, f"  [DEBUG] btn[{ri}][{bi}] text={repr(getattr(b,'text',''))} url={getattr(b,'url',None)} web_app={getattr(b,'web_app',None)}")

    # 2. Bypass safeguard — peer = channel, bot = @safeguard
    await bypass_safeguard(app, target_msg, bot_username=SAFEGUARD_BOT)
    log(idx, "[Join] POST safeguard OK, tunggu invite link dari @safeguard...")

    # 3. Tunggu pesan dari @safeguard yang isinya invite link
    sg_msg = await wait_msg(app, chat=SAFEGUARD_BOT, timeout=30)
    text   = sg_msg.text or sg_msg.caption or ""
    log(idx, f"[Join] @safeguard: {text[:100]}")

    # Ambil t.me/+ invite link
    invite = re.search(r"https://t\.me/\+\S+", text)
    if not invite:
        # Coba dari inline button
        if sg_msg.reply_markup and hasattr(sg_msg.reply_markup, "inline_keyboard"):
            for row in sg_msg.reply_markup.inline_keyboard:
                for btn in row:
                    if btn.url and "t.me" in btn.url:
                        invite_link = btn.url
                        break
        if not invite:
            raise Exception(f"Invite link tidak ditemukan di pesan safeguard: {text[:200]}")
    else:
        invite_link = invite.group(0)

    log(idx, f"[Join] Invite link: {invite_link}")

    # 4. Join
    await app.join_chat(invite_link)
    log(idx, "[Join] Joined group ✓")

# ─── Runner Per Akun ─────────────────────────────────────────────────────────
async def run(idx):
    profile = profiles[idx]
    creds   = twitter_creds[idx] if idx < len(twitter_creds) else None
    app     = Client(f"account_{idx}", api_id=API_ID, api_hash=API_HASH, session_string=sessions[idx])

    try:
        async with app:
            log(idx, "Starting...")

            await app.send_message(BOT, f"/start {START}")
            msg = await wait_msg(app)

            ans = solve_math(msg.text)
            if ans:
                log(idx, f"Math: {msg.text.strip()} → {ans}")
                await app.send_message(BOT, ans)
                msg = await wait_msg(app)

            await click_btn(app, msg)
            msg = await wait_msg(app)

            # Safeguard awal (dari PaygentBot)
            for row in (msg.reply_markup.inline_keyboard if msg.reply_markup and hasattr(msg.reply_markup, "inline_keyboard") else []):
                for btn in row:
                    if hasattr(btn, "web_app") and btn.web_app:
                        log(idx, "Bypassing safeguard (initial)...")
                        await bypass_safeguard(app, msg)
                        await asyncio.sleep(3)

            msg = await wait_msg(app)

            # ── Join group via @paygentuse ──
            if str(idx) not in joined:
                log(idx, "Join group via @paygentuse...")
                await join_group_via_paygentuse(app, idx)
                mark_joined(idx)
                await asyncio.sleep(2)
            else:
                log(idx, "Already joined, skip.")

            # ── Follow di bot Telegram ──
            if str(idx) not in followed:
                log(idx, "Click follow button (TG bot)...")
                await click_btn(app, msg, keyword="follow")
                msg = await wait_msg(app)
            else:
                log(idx, "Already clicked follow, skip.")

            # ── Follow Twitter langsung ──
            if creds:
                log(idx, f"Twitter follow @{FOLLOW_TARGET}...")
                await twitter_follow(creds["auth_token"], creds["ct0"], idx)
                if str(idx) not in followed:
                    mark_followed(idx)
            else:
                log(idx, "No Twitter creds, skip Twitter follow.")
                if str(idx) not in followed:
                    mark_followed(idx)

            # ── Submit details ──
            log(idx, "Submitting details...")
            await app.send_message(BOT, "Submit Your Details")
            await asyncio.sleep(2)

            for val in [profile, apikeys[idx], emails[idx]]:
                await app.send_message(BOT, val)
                await asyncio.sleep(1.5)

            msg = await wait_msg(app)
            await app.send_message(BOT, "Done")
            msg = await wait_msg(app)

            log(idx, "Sending repost...")
            await app.send_message(BOT, gen_repost(profile))
            msg = await wait_msg(app)

            await app.send_message(BOT, "Yes")
            msg = await wait_msg(app)

            log(idx, f"Wallet: {wallets[idx][:8]}...")
            await app.send_message(BOT, wallets[idx])
            msg = await wait_msg(app)

            await app.send_message(BOT, "Complete the Airdrop")

            log(idx, "✓ Done!")

    except Exception as e:
        log(idx, f"✗ Error: {e}")

# ─── Account Selector ─────────────────────────────────────────────────────────
def select_accounts():
    total = len(sessions)
    print()
    print("┌───────────────────────────────────┐")
    print("│     Paygent Airdrop Bot  v6.6     │")
    print("├───────────────────────────────────┤")
    print(f"│  Total akun : {total:<21}│")
    print("├───────────────────────────────────┤")
    print("│  [1] Satu akun                    │")
    print("│  [2] Semua akun                   │")
    print("│  [3] Dari akun X sampai akhir     │")
    print("└───────────────────────────────────┘")
    print("  (Nomor akun mulai dari 1)\n")

    while True:
        choice = input("  Pilih > ").strip()
        if choice == "1":
            try:
                n = int(input(f"  Nomor akun (1–{total}) : ").strip())
                if 1 <= n <= total:
                    return [n - 1]
                print(f"  ✗ Nomor harus 1–{total}")
            except ValueError:
                print("  ✗ Masukkan angka yang valid.")
        elif choice == "2":
            return list(range(total))
        elif choice == "3":
            try:
                n = int(input(f"  Dari nomor akun (1–{total}) : ").strip())
                if 1 <= n <= total:
                    return list(range(n - 1, total))
                print(f"  ✗ Nomor harus 1–{total}")
            except ValueError:
                print("  ✗ Masukkan angka yang valid.")
        else:
            print("  ✗ Pilihan tidak valid. Masukkan 1, 2, atau 3.")

async def main(idxs):
    print(f"\n  ▶ Menjalankan {len(idxs)} akun...\n")
    await asyncio.gather(*[run(i) for i in idxs])
    print("\n  ✓ Semua akun selesai.")

if __name__ == "__main__":
    idxs = select_accounts()
    asyncio.run(main(idxs))
