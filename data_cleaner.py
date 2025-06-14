# -*- coding: utf-8 -*-
"""
Bu betik, TİTCK'dan indirilen çeşitli ham Excel dosyalarını okur,
temizler, standardize eder, kodları metin açıklamalarına çevirir
ve yapay zeka modellerinin kullanabileceği temiz .jsonl formatında kaydeder.

Nihai Sürüm - Tüm kontroller ve son düzeltmeler yapılmıştır.
"""
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

def save_as_jsonl(df, output_filename):
    """DataFrame'i JSONL formatında kaydeder."""
    processed_file_path = PROCESSED_DATA_DIR / output_filename
    df.to_json(processed_file_path, orient='records', lines=True, force_ascii=False)
    logging.info(f"-> Başarıyla '{output_filename}' olarak kaydedildi. ({len(df)} satır)")

# ==============================================================================
# İŞLEYİCİ FONKSİYONLAR
# ==============================================================================

def process_ruhsatli_urunler():
    """Ruhsatlı ürünler listesini işler (Başlık Satırı: 2)."""
    filepath = get_file_path("ruhsatli_ilaclar_listesi.xlsx")
    if not filepath: return True
    
    sheet_name = "RUHSATLI ÜRÜNLER LİSTESİ"
    logging.info(f"'{filepath.name}' -> '{sheet_name}' sayfası işleniyor...")
    try:
        column_map = {'BARKOD': 'barkod', 'ÜRÜN ADI': 'urun_adi', 'ETKİN MADDE': 'etkin_madde', 'ATC KODU': 'atc_kodu', 'RUHSAT SAHİBİ FİRMA': 'ruhsat_sahibi_firma', 'RUHSAT NUMARASI': 'ruhsat_no', 'RUHSAT TARİHİ': 'ruhsat_tarihi'}
        df = pd.read_excel(filepath, sheet_name=sheet_name, header=1, dtype={'BARKOD': str, 'RUHSAT NUMARASI': str})
        
        # Yalnızca column_map içinde tanımlanan ve dosyada mevcut olan sütunları al
        existing_cols = [col for col in column_map.keys() if col in df.columns]
        if not existing_cols:
            logging.error(f"'{sheet_name}' sayfasında belirtilen sütunlardan hiçbiri bulunamadı.")
            return False
        
        df = df[existing_cols]
        df.rename(columns=column_map, inplace=True)
        df