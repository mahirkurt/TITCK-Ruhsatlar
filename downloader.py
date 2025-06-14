# Dosya Adı: downloader.py

import os
import sys
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# --- KULLANICI AYARLARI ---
# Lütfen bu bilgileri kendi giriş bilgilerinizle ve doğru URL'ler ile doldurun
LOGIN_URL = "https://www.titck.gov.tr/giris"
DOWNLOAD_PAGE_URL = "https://www.titck.gov.tr/dinamikmodul/100" # Örnek: Fiyat Listesi sayfası

# Kullanıcı adı ve şifreyi GÜVENLİ bir şekilde ortam değişkenlerinden al
USERNAME = os.getenv("TITCK_USERNAME")
PASSWORD = os.getenv("TITCK_PASSWORD")

# --- Klasör Tanımlamaları ---
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "ham_veriler"
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    # Güvenlik Kontrolü
    if not USERNAME or not PASSWORD:
        print("HATA: TITCK_USERNAME ve TITCK_PASSWORD secret'ları GitHub deposunda tanımlanmamış.")
        sys.exit(1)

    with sync_playwright() as p:
        print("Tarayıcı başlatılıyor...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            print(f"Giriş sayfasına gidiliyor: {LOGIN_URL}")
            page.goto(LOGIN_URL)
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
            
            if dynamic_url.startswith('/'):
                dynamic_url = f"https://www.titck.gov.tr{dynamic_url}"

            print(f"Dinamik URL başarıyla bulundu: {dynamic_url}")
            
            all_cookies = page.context.cookies()
            cookies_dict = {cookie['name']: cookie['value'] for cookie in all_cookies}
            print("Kimlik doğrulama çerezleri tarayıcıdan alındı.")
            
            browser.close()
            print("Tarayıcı kapatıldı.")

        except PlaywrightTimeoutError:
            print(f"HATA: Belirtilen seçici veya sayfa zaman aşımına uğradı. Seçicileri veya URL'leri kontrol edin.")
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
            
            filename = dynamic_url.split('/')[-1]
            if not filename or not filename.endswith((".xlsx", ".xls")):
                filename = "indirilen_detayli_liste.xlsx"

            output_path = OUTPUT_DIR / filename
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"BAŞARILI! Dosya şuraya kaydedildi: {output_path}")
            
        except requests.exceptions.RequestException as e:
            print(f"HATA: Dosya indirilirken bir sorun oluştu: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()