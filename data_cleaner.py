# -*- coding: utf-8 -*-
"""
Bu betik, TİTCK'dan indirilen çeşitli ham Excel dosyalarını okur,
temizler, standardize eder ve yapay zeka modellerinin kullanabileceği
temiz .jsonl formatında kaydeder.

Nihai Sürüm - Kullanıcı direktiflerine göre güncellenmiştir.
"""
import pandas as pd
from pathlib import Path
import sys
import logging

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
    """'ilac_fiyat_listesi.xlsx' dosyasını sizin belirttiğiniz son kurallara göre işler."""
    filename = "ilac_fiyat_listesi.xlsx"
    filepath = get_file_path(filename)
    if not filepath: return True
        
    # Sizin belirttiğiniz sayfa adı
    sheet_name = "REFERANS BAZLI İLAÇ LİSTESİ"
    
    logging.info(f"'{filename}' -> '{sheet_name}' sayfası işleniyor...")
    try:
        # Sizin belirttiğiniz sütunlar ve yeni adları
        column_map = {
            'ILAC ADI': 'urun_adi',
            'FIRMA ADI': 'firma_adi',
            'GERCEK KAYNAK FIYAT (GKF) (€)': 'gkf_eur'
        }
        
        # Başlıkların ilk satırda olduğunu varsayıyoruz (header=0)
        df = pd.read_excel(filepath, sheet_name=sheet_name, header=0, dtype=str)
        
        existing_cols = [col for col in column_map.keys() if col in df.columns]
        if len(existing_cols) < len(column_map):
             missing_keys = set(column_map.keys()) - set(existing_cols)
             logging.error(f"'{sheet_name}' sayfasında şu sütunlar bulunamadı: {missing_keys}")
             return False

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
    filepath = get_file_path(filename)
    if not filepath: return True
    
    sheet_name = "RUHSATLI ÜRÜNLER LİSTESİ"
    logging.info(f"'{filename}' -> '{sheet_name}' sayfası işleniyor...")
    try:
        column_map = {'BARKOD': 'barkod', 'ÜRÜN ADI': 'urun_adi', 'ETKİN MADDE': 'etkin_madde'}
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
        
def main():
    """Tüm veri temizleme işlemlerini yürüten ana fonksiyon."""
    logging.info("===== Veri Temizleme ve Standardizasyon Başlatıldı =====")
    
    # Sadece belirttiğiniz dosyaları işleyecek şekilde güncellendi
    results = [
        process_ilac_fiyat_listesi(),
        process_ruhsatli_urunler(),
        # Diğer dosyaları işlemek için fonksiyonlar buraya eklenebilir.
    ]
    
    if all(results):
        logging.info("===== Tüm Dosyalar Başarıyla İşlendi =====")
    else:
        logging.error("!!! Bazı dosyalar işlenirken hatalar oluştu. Lütfen logları kontrol edin. !!!")
        sys.exit(1)


if __name__ == "__main__":
    main()
