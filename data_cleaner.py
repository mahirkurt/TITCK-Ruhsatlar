# -*- coding: utf-8 -*-
import pandas as pd
from pathlib import Path
import sys
import logging
import re
import numpy as np

# --- Loglama ve Klasör Kurulumu ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] - %(message)s", stream=sys.stdout)
BASE_DIR = Path(__file__).resolve().parent
RAW_DATA_DIR = BASE_DIR / "ham_veriler"
PROCESSED_DATA_DIR = BASE_DIR / "islenmis_veriler"
RAW_DATA_DIR.mkdir(exist_ok=True)
PROCESSED_DATA_DIR.mkdir(exist_ok=True)


def get_file_path(filename):
    """Dosya yolunu oluşturur ve varlığını kontrol eder."""
    path = RAW_DATA_DIR / filename
    if not path.exists():
        logging.warning(f"Kaynak dosya bulunamadı, atlanıyor: {path}")
        return None
    return path

def save_as_jsonl(df, output_filename, original_filename=""):
    """DataFrame'i JSONL formatında kaydeder."""
    processed_file_path = PROCESSED_DATA_DIR / output_filename
    df.to_json(processed_file_path, orient='records', lines=True, force_ascii=False)
    logging.info(f"-> '{original_filename}' başarıyla '{output_filename}' olarak kaydedildi. ({len(df)} satır)")

# ==============================================================================
# İŞLEYİCİ FONKSİYONLAR
# ==============================================================================

def process_ilac_fiyat_listesi():
    """'ilac_fiyat_listesi.xlsx' dosyasını doğru sayfa ve sütunlarla işler."""
    filename = "ilac_fiyat_listesi.xlsx"
    filepath = get_file_path(filename)
    if not filepath: return True
        
    # --- DÜZELTİLMİŞ BİLGİLER ---
    sheet_name = "REFERANS BAZLI İLAÇ LİSTESİ"
    header_row = 1 # Başlıklar 2. satırda
    column_map = {
        'BARKOD': 'barkod', 
        'ÜRÜN ADI': 'urun_adi', 
        'KAMU FİYATI': 'kamu_fiyati', 
        'KAMU ÖDENEN': 'kamu_odenen', 
        'DEPOCU FİYATI': 'depocu_fiyati', 
        'İMALATÇI FİYATI': 'imalatci_fiyati'
    }
    # ---------------------------

    logging.info(f"'{filename}' -> '{sheet_name}' sayfası işleniyor...")
    try:
        df = pd.read_excel(filepath, sheet_name=sheet_name, header=header_row, dtype={'BARKOD': str})
        
        existing_cols = [col for col in column_map.keys() if col in df.columns]
        df = df[existing_cols]
        df.rename(columns=column_map, inplace=True)
        df.dropna(how='all', inplace=True)

        save_as_jsonl(df, "ilac_fiyatlari.jsonl", filename)
        return True
    except Exception as e:
        logging.error(f"'{sheet_name}' işlenirken KRİTİK HATA: {e}")
        return False

def process_ruhsatli_urunler():
    """Ruhsatlı ürünler listesini işler."""
    filename = "ruhsatli_ilaclar_listesi.xlsx"
    # ... (Bu fonksiyonun geri kalanı öncekiyle aynı, değişiklik yok)
    filepath = get_file_path(filename)
    if not filepath: return True
    
    sheet_name = "RUHSATLI ÜRÜNLER LİSTESİ"
    logging.info(f"'{filename}' -> '{sheet_name}' sayfası işleniyor...")
    try:
        column_map = {'BARKOD': 'barkod', 'ÜRÜN ADI': 'urun_adi', 'ETKİN MADDE': 'etkin_madde', 'ATC KODU': 'atc_kodu', 'RUHSAT SAHİBİ FİRMA': 'ruhsat_sahibi_firma'}
        df = pd.read_excel(filepath, sheet_name=sheet_name, header=1, dtype={'BARKOD': str})
        
        existing_cols = [col for col in column_map.keys() if col in df.columns]
        df = df[existing_cols]
        df.rename(columns=column_map, inplace=True)
        df.dropna(how='all', inplace=True)

        save_as_jsonl(df, "ruhsatli_urunler.jsonl", filename)
        return True
    except Exception as e:
        logging.error(f"'{sheet_name}' işlenirken KRİTİK HATA: {e}")
        return False

def process_etkin_maddeler():
    """Etkin madde listesini işler."""
    filename = "etkin_madde_listesi.xlsx"
    # ... (Bu fonksiyonun geri kalanı öncekiyle aynı, değişiklik yok)
    filepath = get_file_path(filename)
    if not filepath: return True

    sheet_name = "Sheet1"
    logging.info(f"'{filename}' -> '{sheet_name}' sayfası işleniyor...")
    try:
        column_map = {'Etkin Madde Adı': 'etkin_madde_adi', 'Sayı': 'basvuru_dosyasi_sayisi'}
        df = pd.read_excel(filepath, sheet_name=sheet_name, header=5, skipfooter=1)
        
        df = df[list(column_map.keys())]
        df.rename(columns=column_map, inplace=True)
        df.dropna(how='all', inplace=True)

        save_as_jsonl(df, "etkin_maddeler.jsonl", filename)
        return True
    except Exception as e:
        logging.error(f"'{sheet_name}' işlenirken KRİTİK HATA: {e}")
        return False
        
def main():
    """Tüm veri temizleme işlemlerini yürüten ana fonksiyon."""
    logging.info("===== Veri Temizleme ve Standardizasyon Başlatıldı =====")
    
    # İşlenecek tüm dosyalar için ilgili fonksiyonları çağır
    results = [
        process_ilac_fiyat_listesi(),
        process_ruhsatli_urunler(),
        process_etkin_maddeler(),
        # ... İhtiyaç duyulan diğer fonksiyon çağrıları buraya eklenebilir
    ]
    
    if all(results):
        logging.info("===== Tüm Dosyalar Başarıyla İşlendi =====")
    else:
        logging.error("!!! Bazı dosyalar işlenirken hatalar oluştu. Lütfen logları kontrol edin. !!!")
        sys.exit(1)

if __name__ == "__main__":
    main()
