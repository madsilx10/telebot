from pyrogram import Client
import os

API_ID = int(input("Masukkan API ID: "))
API_HASH = input("Masukkan API Hash: ")

print("\n=== GENERATE SESSION STRING ===")
print("Masukkan nomor HP format internasional (contoh: +628123456789)")
print("Ulangi untuk tiap akun, ketik 'done' untuk selesai\n")

sessions = []

while True:
    phone = input("Nomor HP (atau 'done' untuk selesai): ").strip()
    if phone.lower() == 'done':
        break

    with Client(
        name=f"temp_{phone.replace('+', '')}",
        api_id=API_ID,
        api_hash=API_HASH,
        phone_number=phone,
        in_memory=True
    ) as app:
        session_string = app.export_session_string()
        sessions.append(session_string)
        print(f"✅ Session berhasil dibuat untuk {phone}")

    # Hapus file session temp kalau ada
    temp_file = f"temp_{phone.replace('+', '')}.session"
    if os.path.exists(temp_file):
        os.remove(temp_file)

# Simpen ke sessions.txt
with open("sessions.txt", "a") as f:
    for s in sessions:
        f.write(s + "\n")

print(f"\n✅ {len(sessions)} session berhasil disimpan ke sessions.txt")
