import os
import sys
import requests
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import stealth_sync

# --- KULLANICI AYARLARI ---
LOGIN_URL = "https://www.titck.gov.tr/giris"
DOWNLOAD_PAGE_URL = "https://www.titck.gov.tr/dinamikmodul/100" # Örnek indirme sayfası

# Kullanıcı adı ve şifreyi GÜVENLİ bir şekilde ortam değişkenlerinden al
USERNAME = os.getenv("TITCK_USERNAME")
PASSWORD = os.getenv("TITCK_PASSWORD")

# --- Klasör Tanımlamaları ---
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "ham_veriler"
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    """Ana otomasyon fonksiyonu"""
    # Güvenlik Kontrolü
    if not USERNAME or not PASSWORD:
        print("HATA: TITCK_USERNAME ve TITCK_PASSWORD ortam değişkenleri tanımlanmamış.")
        print("Lütfen PowerShell'de $env: komutları ile değişkenleri ayarladığınızdan emin olun.")
        sys.exit(1)

    with sync_playwright() as p:
        print("Tarayıcı başlatılıyor (Stealth Modu Aktif)...")
        # YERELDE TEST EDERKEN NELER OLDUĞUNU GÖRMEK İÇİN headless=False YAPABİLİRSİNİZ
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Tarayıcı izlerini gizle
        stealth_sync(page)

        try:
            print(f"Giriş sayfasına gidiliyor: {LOGIN_URL}")
            page.goto(LOGIN_URL, timeout=90000)
            
            print("Giriş formunun yüklenmesi bekleniyor (60 saniyeye kadar)...")
            page.wait_for_selector("#kullaniciAdi", timeout=60000)

            print("Kullanıcı adı ve şifre giriliyor...")
            page.fill("#kullaniciAdi", USERNAME)
            page.fill("#sifre", PASSWORD)
            page.click("button[type='submit']")
            
            print("Giriş yapılıyor, sayfanın yüklenmesi bekleniyor...")
            page.wait_for_load_state("networkidle", timeout=30000)

            print(f"Dosya indirme sayfasına gidiliyor: {DOWNLOAD_PAGE_URL}")
            page.goto(DOWNLOAD_PAGE_URL)
            
            # KULLANICI NOTU: İndirme linkinin metnini veya benzersiz bir özelliğini buraya yazın.
            print("İndirme linki aranıyor...")
            download_link_locator = page.locator("a:has-text('Detaylı Fiyat Listesi')") # ÖRNEKTİR
            download_link_locator.wait_for(timeout=15000)
            dynamic_url = download_link_locator.get_attribute("href")
            
            if dynamic_url and dynamic_url.startswith('/'):
                dynamic_url = f"https://www.titck.gov.tr{dynamic_url}"

            print(f"Dinamik URL başarıyla bulundu: {dynamic_url}")
            
            all_cookies = page.context.cookies()
            cookies_dict = {cookie['name']: cookie['value'] for cookie in all_cookies}
            print("Kimlik doğrulama çerezleri tarayıcıdan alındı.")
            
            browser.close()
            print("Tarayıcı kapatıldı.")

        except PlaywrightTimeoutError:
            print(f"HATA: Belirtilen seçici veya sayfa zaman aşımına uğradı. Anti-bot koruması hala aktif olabilir.")
            page.screenshot(path="debug_screenshot.png")
            print("Hata anının ekran görüntüsü 'debug_screenshot.png' olarak kaydedildi.")
            browser.close()
            sys.exit(1)
        except Exception as e:
            print(f"Tarayıcı otomasyonu sırasında bir hata oluştu: {e}")
            browser.close()
            sys.exit(1)

        print("Dosya 'requests' kütüphanesi ile indiriliyor...")
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'}
            response = requests.get(dynamic_url, cookies=cookies_dict, headers=headers)
            response.raise_for_status()
            
            filename = "indirilen_detayli_liste.xlsx" # Dosya adını sabitliyoruz
            output_path = OUTPUT_DIR / filename
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"BAŞARILI! Dosya şuraya kaydedildi: {output_path}")
            
        except requests.exceptions.RequestException as e:
            print(f"HATA: Dosya indirilirken bir sorun oluştu: {e}")
            sys.exit(1)

# --- EN ÖNEMLİ KISIM ---
# Bu blok, betiğin `python downloader.py` komutuyla çalıştırıldığında
# yukarıdaki `main()` fonksiyonunu çağırmasını sağlar.
if __name__ == "__main__":
    main()