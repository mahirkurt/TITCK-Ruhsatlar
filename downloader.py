# downloader.py (2Captcha Entegrasyonlu Nihai Hali)

import os
import sys
import requests
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from twocaptcha import TwoCaptcha # <-- YENİ EKLENDİ

# --- KULLANICI AYARLARI ---
LOGIN_URL = "https://www.titck.gov.tr/giris"
DOWNLOAD_PAGE_URL = "https://www.titck.gov.tr/dinamikmodul/100"

# Tüm gizli bilgileri GÜVENLİ bir şekilde ortam değişkenlerinden al
USERNAME = os.getenv("TITCK_USERNAME")
PASSWORD = os.getenv("TITCK_PASSWORD")
TWOCAPTCHA_API_KEY = os.getenv("TWOCAPTCHA_API_KEY")

# --- Klasör Tanımlamaları ---
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "ham_veriler"
OUTPUT_DIR.mkdir(exist_ok=True)


def solve_turnstile_captcha(page):
    """Sayfadaki Cloudflare Turnstile CAPTCHA'sını 2Captcha ile çözer."""
    print("Cloudflare Turnstile CAPTCHA tespit edildi. 2Captcha servisine gönderiliyor...")
    
    # 2Captcha solve konfigürasyonu
    config = {
        'apiKey': TWOCAPTCHA_API_KEY,
        'defaultTimeout': 120,
        'pollingInterval': 5,
    }
    solver = TwoCaptcha(**config)

    try:
        # CAPTCHA'nın site anahtarını (sitekey) HTML'den bul
        sitekey_element = page.locator(".cf-turnstile")
        sitekey = sitekey_element.get_attribute("data-sitekey")
        
        if not sitekey:
            print("HATA: CAPTCHA sitekey bulunamadı.")
            return False

        print(f"Sitekey bulundu: {sitekey}")

        # Çözüm için isteği gönder
        result = solver.turnstile(
            sitekey=sitekey,
            url=page.url
        )

        print(f"CAPTCHA çözüldü! Token alınıyor...")
        captcha_response_token = result['code']

        # Çözüm token'ını sayfadaki gizli alana enjekte et
        js_script = f'document.querySelector("[name=\'cf-turnstile-response\']").value = "{captcha_response_token}";'
        page.evaluate(js_script)
        
        print("Token başarıyla sayfaya enjekte edildi.")
        return True

    except Exception as e:
        print(f"CAPTCHA çözülürken bir hata oluştu: {e}")
        return False


def main():
    if not all([USERNAME, PASSWORD, TWOCAPTCHA_API_KEY]):
        print("HATA: Gerekli tüm secret'lar (USERNAME, PASSWORD, TWOCAPTCHA_API_KEY) GitHub'da tanımlanmamış.")
        sys.exit(1)

    with sync_playwright() as p:
        print("Tarayıcı başlatılıyor...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            print(f"Giriş sayfasına gidiliyor: {LOGIN_URL}")
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)

            # Sayfada CAPTCHA var mı diye 5 saniye bekle ve kontrol et
            time.sleep(5)
            if page.locator(".cf-turnstile").is_visible():
                if not solve_turnstile_captcha(page):
                    raise Exception("CAPTCHA çözme işlemi başarısız oldu.")
                # CAPTCHA çözüldükten sonra sayfanın toparlanması için biraz bekle
                time.sleep(3)
            else:
                print("CAPTCHA tespit edilmedi, normal giriş deneniyor.")

            # Giriş formunu doldurma
            print("Giriş formunun yüklenmesi bekleniyor...")
            page.wait_for_selector("#kullaniciAdi", timeout=10000)
            print("Kullanıcı adı ve şifre giriliyor...")
            page.fill("#kullaniciAdi", USERNAME)
            page.fill("#sifre", PASSWORD)
            page.click("button[type='submit']")
            
            # ... (Bundan sonraki indirme adımları aynı) ...
            
            print("Giriş yapılıyor, sayfanın yüklenmesi bekleniyor...")
            page.wait_for_load_state("networkidle", timeout=30000)

            print(f"Dosya indirme sayfasına gidiliyor: {DOWNLOAD_PAGE_URL}")
            page.goto(DOWNLOAD_PAGE_URL)
            
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

        except Exception as e:
            print(f"Ana otomasyon bloğunda bir hata oluştu: {e}")
            page.screenshot(path="debug_screenshot.png")
            print("Hata anının ekran görüntüsü 'debug_screenshot.png' olarak kaydedildi.")
            browser.close()
            sys.exit(1)

        # ... (requests ile indirme kısmı aynı kalıyor) ...

# ... if __name__ == "__main__": main() kısmı aynı kalıyor ...