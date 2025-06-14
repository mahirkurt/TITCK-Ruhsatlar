# downloader.py (Son Bekleme Mantığı Eklenmiş Nihai Hali)

import os
import sys
import requests
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# --- KULLANICI AYARLARI ---
LOGIN_URL = "https://ebs.titck.gov.tr/Login/Login" # Doğru giriş URL'si
DOWNLOAD_PAGE_URL = "https://www.titck.gov.tr/dinamikmodul/100" # Örnek

# Gizli bilgileri ortam değişkenlerinden al
USERNAME = os.getenv("TITCK_USERNAME")
PASSWORD = os.getenv("TITCK_PASSWORD")

# --- Klasör Tanımlamaları ---
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "ham_veriler"
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    if not USERNAME or not PASSWORD:
        print("HATA: TITCK_USERNAME ve TITCK_PASSWORD ortam değişkenleri tanımlanmamış.")
        sys.exit(1)

    with sync_playwright() as p:
        print("Tarayıcı başlatılıyor...")
        # TEST İÇİN BU SATIRI headless=False YAPABİLİRSİNİZ
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            print(f"Giriş sayfasına gidiliyor: {LOGIN_URL}")
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(3) # Sayfanın oturması için kısa bir bekleme

            # CAPTCHA kontrolü
            captcha_input_locator = page.locator("#GuvenlikKodu")
            if captcha_input_locator.is_visible(timeout=5000): # 5 saniye içinde görünürse
                raise Exception("HATA: Sayfada beklenmedik bir şekilde CAPTCHA bulundu. Site güvenliği değişmiş olabilir.")
            else:
                print("CAPTCHA alanı bulunamadı. Normal giriş deneniyor.")

            # --- NİHAİ DÜZELTME: DOLDURMADAN ÖNCE BEKLEME ---
            print("Giriş formunun etkileşime hazır olması bekleniyor...")
            kullanici_adi_input = page.locator("#kullaniciAdi")
            # Doldurmadan önce, alanın sayfada gerçekten görünür olmasını bekle.
            kullanici_adi_input.wait_for(state="visible", timeout=30000)
            print("Form hazır. Kullanıcı adı ve şifre giriliyor...")
            # ----------------------------------------------------

            kullanici_adi_input.fill(USERNAME)
            page.fill("#sifre", PASSWORD)
            
            print("Giriş butonuna tıklanıyor...")
            page.click("button[type='submit']")
            
            print("Giriş yapılıyor, sayfanın yüklenmesi bekleniyor...")
            page.wait_for_load_state("networkidle", timeout=30000)

            # Girişin başarılı olup olmadığını kontrol et
            if "Login" in page.title() or "Giriş" in page.title():
                 raise Exception("Giriş başarısız oldu, hala giriş sayfasındayız. Kullanıcı adı/şifre hatalı olabilir.")
            print("Giriş başarılı!")

            # ... İndirme adımları buraya eklenecek ...
            # Örnek:
            print(f"Dosya indirme sayfasına gidiliyor: {DOWNLOAD_PAGE_URL}")
            page.goto(DOWNLOAD_PAGE_URL)
            print("İndirme linki aranıyor...")
            download_link_locator = page.locator("a:has-text('Detaylı Fiyat Listesi')") # ÖRNEKTİR
            download_link_locator.wait_for(timeout=15000)
            # ... geri kalan indirme ve kaydetme kodları ...
            
            print("Tüm işlemler başarıyla tamamlandı.")
            browser.close()

        except Exception as e:
            print(f"Ana otomasyon bloğunda bir hata oluştu: {e}")
            page.screenshot(path="debug_screenshot.png")
            print("Hata anının ekran görüntüsü 'debug_screenshot.png' olarak kaydedildi.")
            browser.close()
            sys.exit(1)


if __name__ == "__main__":
    main()