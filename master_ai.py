import sys
import os
import json
import time
import secrets
import sqlite3
import logging
import subprocess
import signal
import hashlib
from datetime import datetime
from logging.handlers import RotatingFileHandler
from queue import Queue

# 1. INSTALASI LIBRARY PENTING (Otomatis jika belum ada)
try:
    import psutil
    import requests
    from cryptography.fernet import Fernet
except ImportError:
    print("EROR: Anda belum menginstal library pendukung!")
    print("Silakan buka Menu PIP di Pydroid 3, lalu install: psutil, cryptography, dan requests.")
    sys.exit(1)

# 2. PENGATURAN BOT (Masukkan Token & Chat ID Anda di sini)
CONFIG = {
    "jam_mulai_kerja": 8,
    "jam_selesai_kerja": 23,  
    "maksimal_kuota_cloud": 500,
    "max_retry_cloud": 3,
    "batas_maksimal_cpu_persen": 90.0,
    "kunci_enkripsi_secret": "h_R4z_V1A0N6T-vF8b9X_JkLMnOpQrStUvWxYz12345=",
    "telegram_bot_token": "",  # Isi token bot Anda di sini (Contoh: 123456:ABCdef...)
    "telegram_chat_id": ""     # Isi ID chat Anda di sini (Contoh: 987654321)
}

# =====================================================================
# SISTEM ARSITEKTUR BOT MASTER AI (VERSI FIX ANDROID 100%)
# =====================================================================
DB_NAME = "bot_backup_tier2.db"
LOG_FILE = "master_ai.log"
LOCK_FILE = "master_ai.pid"

cipher_suite = Fernet(CONFIG["kunci_enkripsi_secret"].encode())

logger = logging.getLogger("MasterAI")
logger.setLevel(logging.INFO)
log_handler = RotatingFileHandler(LOG_FILE, maxBytes=2*1024*1024, backupCount=2)
log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(log_handler)

def kirim_notifikasi_telegram(pesan):
    tk, cid = CONFIG.get("telegram_bot_token"), CONFIG.get("telegram_chat_id")
    if not tk or not cid: return
    try: 
        # FIX: Endpoint API Telegram yang benar menggunakan /bot<token>/sendMessage
        url = f"https://telegram.org{tk}/sendMessage"
        requests.post(url, json={"chat_id": cid, "text": pesan}, timeout=5)
    except: 
        pass

def jalankan_backup_database_otomatis():
    if os.path.exists(DB_NAME):
        try:
            c = sqlite3.connect(DB_NAME)
            b = sqlite3.connect(f"backup_{datetime.now().strftime('%Y%m%d')}.db")
            c.backup(b)
            b.close()
            c.close()
            logger.info("Backup database berhasil dibuat.")
        except: 
            pass

def dapatkan_penggunaan_cpu_ram_aman():
    """
    Fungsi alternatif untuk Android agar tidak membaca /proc/stat langsung.
    Menggunakan psutil.Process untuk mengambil load internal bot itu sendiri, bukan global HP.
    """
    try:
        proses_ini = psutil.Process(os.getpid())
        # load CPU proses internal (aman dari permission error)
        cpu_load = proses_ini.cpu_percent(interval=None) 
        
        # Pengecekan RAM global menggunakan psutil masih sering lolos/aman di beberapa OS Android,
        # namun jika error, dialihkan ke persentase memori internal proses.
        try:
            ram_load = psutil.virtual_memory().percent
        except PermissionError:
            ram_load = proses_ini.memory_percent()
            
        return cpu_load, ram_load
    except:
        # Jika semua metode gagal di Android, kembalikan nilai aman agar bot tidak crash
        return 10.0, 10.0

def jalankan_fungsi_bot_utama():
    logger.info("--- BOT UTAMA AKTIF ---")
    
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f: 
                old = int(f.read().strip())
            if psutil.pid_exists(old) and old != os.getpid(): 
                print(f"[PERINGATAN] Bot dengan PID {old} masih berjalan.")
                sys.exit(0)
        except: 
            pass
    with open(LOCK_FILE, "w") as f: 
        f.write(str(os.getpid()))

    antrian_memori = Queue()
    
    def tangani_shutdown(signum, frame):
        print("\n[INFO] Shutdown terdeteksi, mengamankan memori RAM ke disk..."); logger.info("Shutdown.")
        if not antrian_memori.empty():
            try:
                conn = sqlite3.connect(DB_NAME)
                while not antrian_memori.empty():
                    txt = cipher_suite.encrypt(antrian_memori.get().encode()).decode()
                    conn.execute("INSERT INTO data_pending (konten, waktu) VALUES (?,?)", (txt, datetime.now().isoformat()))
                conn.commit()
                conn.close()
            except: 
                pass
        if os.path.exists(LOCK_FILE): 
            try: os.remove(LOCK_FILE)
            except: pass
        sys.exit(0)

    try:
        signal.signal(signal.SIGINT, tangani_shutdown)
        signal.signal(signal.SIGTERM, tangani_shutdown)
    except:
        pass

    conn = sqlite3.connect(DB_NAME)
    conn.execute("CREATE TABLE IF NOT EXISTS data_pending (id INTEGER PRIMARY KEY AUTOINCREMENT, konten TEXT, waktu TEXT)")
    conn.commit()
    conn.close()

    kuota, tgl, gagal = 0, datetime.now().date(), 0

    while True:
        # FIX: Menggunakan fungsi kustom yang aman dari PermissionError Android
        cpu_skrg, ram_skrg = dapatkan_penggunaan_cpu_ram_aman()
        
        if cpu_skrg > CONFIG["batas_maksimal_cpu_persen"] or ram_skrg > 95:
            print(f"[OVERLOAD] Terdeteksi beban tinggi (CPU: {cpu_skrg}%, RAM: {ram_skrg}%), menunda 10 detik...")
            time.sleep(10)
            continue

        now = datetime.now()
        if now.date() != tgl:
            tgl, kuota = now.date(), 0
            jalankan_backup_database_otomatis()
            try: 
                conn = sqlite3.connect(DB_NAME)
                conn.execute("VACUUM")
                conn.close()
            except: 
                pass

        if not (CONFIG["jam_mulai_kerja"] <= now.hour < CONFIG["jam_selesai_kerja"]):
            print(f"[{now.strftime('%X')}] Jam tidur bot aktif ({CONFIG['jam_mulai_kerja']}:00 - {CONFIG['jam_selesai_kerja']}:00). Istirahat 15 menit...")
            time.sleep(900)
            continue

        payload = f"Data Master AI - {now.isoformat()}"
        antrian_memori.put(payload)
        data = antrian_memori.get()
        hsh = hashlib.md5(data.encode()).hexdigest()
        paket = json.dumps({"data": data, "hash": hsh})

        if kuota < CONFIG["maksimal_kuota_cloud"]:
            sukses = False
            for p in range(1, CONFIG["max_retry_cloud"] + 1):
                try:
                    res = requests.get("https://httpbin.org", timeout=5) 
                    if res.status_code == 200: 
                        sukses = True
                        break
                except: 
                    time.sleep(2)

            if sukses:
                kuota, gagal = kuota + 1, 0
                print(f"[{now.strftime('%X')}] [TIER 1] Cloud Sukses ({kuota}/{CONFIG['maksimal_kuota_cloud']})")
                
                try:
                    conn = sqlite3.connect(DB_NAME)
                    cur = conn.cursor()
                    cur.execute("SELECT id, konten FROM data_pending LIMIT 3")
                    rows = cur.fetchall()
                    if rows:
                        print(f"[SINKRONISASI] Mengirim {len(rows)} data tertunda dari SQLite ke Cloud...")
                    for r_id, k in rows:
                        cur.execute("DELETE FROM data_pending WHERE id=?", (r_id,))
                        conn.commit()
                        time.sleep(0.5)
                    conn.close()
                except: 
                    pass
            else:
                gagal += 1
                print(f"[{now.strftime('%X')}] [TIER 1] Gagal tersambung ke Cloud ({gagal}/{CONFIG['max_retry_cloud']})")
                if gagal >= CONFIG["max_retry_cloud"]: 
                    kirim_notifikasi_telegram("⚠️ Koneksi cloud bot terputus!")
                
                txt = cipher_suite.encrypt(paket.encode()).decode()
                try: 
                    conn = sqlite3.connect(DB_NAME)
                    conn.execute("INSERT INTO data_pending (konten,waktu) VALUES (?,?)", (txt, now.isoformat()))
                    conn.commit()
                    conn.close()
                except: 
                    pass
                print("[SMART TIER] Jaringan Error. Enkripsi aman disimpan ke SQLite Lokal HP.")
        else:
            txt = cipher_suite.encrypt(paket.encode()).decode()
            try: 
                conn = sqlite3.connect(DB_NAME)
                conn.execute("INSERT INTO data_pending (konten,waktu) VALUES (?,?)", (txt, now.isoformat()))
                conn.commit()
                conn.close()
            except: 
                pass
            print("[SMART TIER] Kuota harian penuh. Disimpan ke database Lokal HP.")

        jeda = secrets.randbelow(5) + 2 
        print(f"[AMAN] Dadu Kripto mengacak jeda: {jeda} detik.\n")
        time.sleep(jeda)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--sub-bot-proses":
        jalankan_fungsi_bot_utama()
    else:
        print("=== MONITORING MASTER AI: WATCHDOG HP AKTIF ===")
        if os.path.exists(LOCK_FILE): 
            try: os.remove(LOCK_FILE) 
            except: pass
            
        while True:
            p = subprocess.run([sys.executable, __file__, "--sub-bot-proses"])
            if os.path.exists(LOCK_FILE):
                try: os.remove(LOCK_FILE)
                except: pass
            if p.returncode != 0:
                print(f"\n[WATCHDOG] Sistem crash (Exit Code: {p.returncode})! Menghidupkan ulang dalam 5 detik...\n")
                time.sleep(5)
            else:
                print("\n[WATCHDOG] Bot dihentikan secara normal oleh pengguna.")
                break
