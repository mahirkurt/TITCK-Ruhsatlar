# downloader.py (Resimli CAPTCHA Çözücülü Nihai Hali)

import os
import sys
import requests
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from twocaptcha import TwoCaptcha

# --- KULLANICI AYARLARI ---
LOGIN_URL = "https://ebs.titck.gov.tr/Login/Login" # Ekran görüntüsündeki doğru URL
DOWNLOAD_PAGE_URL = "https://www.titck.gov.tr/dinamikmodul/100" # Örnek indirme sayfası

# Tüm gizli bilgileri GÜVENLİ bir şekilde ortam değişkenlerinden al
USERNAME = os.getenv("TITCK_USERNAME")
PASSWORD = os.getenv("TITCK_PASSWORD")
TWOCAPTCHA_API_KEY = os.getenv("TWOCAPTCHA_API_KEY")

# --- Klasör Tanımlamaları ---
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "ham_veriler"
CAPTCHA_IMAGE_PATH = BASE_DIR / "captcha_image.png"
OUTPUT_DIR.mkdir(exist_ok=True)


def solve_image_captcha(page, api_key):
    """Sayfadaki resimli CAPTCHA'yı 2Captcha ile çözer."""
    print("Resimli CAPTCHA tespit edildi. Ekran görüntüsü alınıyor...")
    
    try:
        # KULLANICI NOTU: CAPTCHA resminin seçicisini doğrulayın. Genellikle bir 'id'si olur.
        captcha_element = page.locator("#imgCaptcha") # Örnek seçici, doğrusuyla değiştirin
        captcha_element.wait_for(timeout=10000)
        captcha_element.screenshot(path=CAPTCHA_IMAGE_PATH)
        print(f"CAPTCHA resmi '{CAPTCHA_IMAGE_PATH}' olarak kaydedildi.")

        print("Resim 2Captcha servisine gönderiliyor...")
        config = {'apiKey': api_key, 'defaultTimeout': 120, 'pollingInterval': 5}
        solver = TwoCaptcha(**config)
        result = solver.normal(str(CAPTCHA_IMAGE_PATH))
        
        captcha_text = result['code']
        print(f"CAPTCHA çözüldü! Çözüm: {captcha_text}")
        return captcha_text

    except Exception as e:
        print(f"CAPTCHA çözülürken bir hata oluştu: {e}")
        return None


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

            # 1. Adım: CAPTCHA'yı Çöz
            captcha_solution = solve_image_captcha(page, TWOCAPTCHA_API_KEY)
            if not captcha_solution:
                raise Exception("CAPTCHA çözme işlemi başarısız oldu.")

            # 2. Adım: Formu Doldur
            print("Giriş formu dolduruluyor...")
            page.fill("#kullaniciAdi", USERNAME)
            page.fill("#sifre", PASSWORD)
            # KULLANICI NOTU: Güvenlik Kodu input alanının seçicisini doğrulayın.
            page.fill("#GuvenlikKodu", captcha_solution) # Örnek seçici, doğrusuyla değiştirin
            
            # 3. Adım: Giriş Yap
            page.click("button[type='submit']")
            
            print("Giriş yapılıyor, sayfanın yüklenmesi bekleniyor...")
            page.wait_for_load_state("networkidle", timeout=30000)

            # Girişin başarılı olup olmadığını kontrol et (Örneğin sayfa başlığı değişir)
            if "Login" in page.title():
                 raise Exception("Giriş başarısız oldu, hala giriş sayfasındayız. CAPTCHA veya şifre yanlış olabilir.")
            print("Giriş başarılı!")

            # ... (Bundan sonraki indirme adımları aynı) ...
            
        except Exception as e:
            print(f"Ana otomasyon bloğunda bir hata oluştu: {e}")
            page.screenshot(path="debug_screenshot.png")
            print("Hata anının ekran görüntüsü 'debug_screenshot.png' olarak kaydedildi.")
            browser.close()
            sys.exit(1)
        
        # Tarayıcı işimiz bitti, kapatabiliriz.
        # Dosya indirme işini requests ile yapmak daha stabil olabilir.
        # Önceki kodumuzdaki gibi devam edilebilir veya doğrudan Playwright ile de indirilebilir.
        # Şimdilik süreci tamamlamak adına browser'ı burada kapatalım.
        print("Tüm tarayıcı işlemleri başarıyla tamamlandı.")
        browser.close()


if __name__ == "__main__":
    main()