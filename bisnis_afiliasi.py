def dapatkan_link_afiliasi(topik_konten):
    """
    LOGIKA AFILIASI ASLI: Robot mencocokkan kata kunci tren 
    dengan link komisi Shopee Affiliate Anda yang sudah dikunci aman.
    """
    # DATABASE LINK SHOPEE AFFILIATE ASLI MILIK ANDA
    database_afiliasi = {
        "baju": "https://s.shopee.co.id/18gCxAEyX",
        "makeup": "https://s.shopee.co.id/18gCxAEyX",
        "gadget": "https://s.shopee.co.id/18gCxAEyX",
        "umum": "https://s.shopee.co.id/18gCxAEyX"
    }
    
    topik_lowercase = topik_konten.lower()
    
    if "dance" in topik_lowercase or "artis" in topik_lowercase:
        return database_afiliasi["makeup"]
    elif "hp" in topik_lowercase or "teknologi" in topik_lowercase:
        return database_afiliasi["gadget"]
    elif "style" in topik_lowercase or "outfit" in topik_lowercase:
        return database_afiliasi["baju"]
    else:
        return database_afiliasi["umum"]


# --- ROBOT AFILIASI & KONTEN OTOMATIS AKTIF (AKUN CADANGAN) ---
print("🤖 ROBOT AFILIASI AKTIF DI SERVER GITHUB...\n")

konten_trending = "Yeonjun - Ice Cream MV Dance Challenge TikTok"
kategori_sekarang = "YouTube Shorts"
postingan_ke = 1

# 1. Mengambil link komisi resmi Anda
link_komisi_anda = dapatkan_link_afiliasi(konten_trending)

# 2. Menghitung jeda aman otomatis agar tidak terblokir
