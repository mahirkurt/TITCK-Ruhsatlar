# -*- coding: utf-8 -*-
"""
Bu betik, TİTCK'dan indirilen çeşitli ham Excel dosyalarını okur,
temizler, standardize eder ve yapay zeka modellerinin kullanabileceği
temiz .jsonl formatında kaydeder.

Nihai Sürüm - Tüm fonksiyonlar bağımsız ve kontrolleri yapılmıştır.
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

# ==============================================================================
# İŞLEYİCİ FONKSİYONLAR
# ==============================================================================

def process_ruhsatli_urunler():
    """Ruhsatlı ürünler listesini işler (Başlık Satırı: 2)."""
    filename = "ruhsatli_ilaclar_listesi.xlsx"
    sheet_name = "RUHSATLI ÜRÜNLER LİSTESİ"
    output_filename = "ruhsatli_urunler.jsonl"
    
    filepath = RAW_DATA_DIR / filename
    if not filepath.exists():
        logging.warning(f"Kaynak dosya bulunamadı, atlanıyor: {filepath}")
        return True
    
    logging.info(f"'{filename}' -> '{sheet_name}' sayfası işleniyor...")
    try:
        column_map = {'BARKOD': 'barkod', 'ÜRÜN ADI': 'urun_adi', 'ETKİN MADDE': 'etkin_madde', 'ATC KODU': 'atc_kodu', 'RUHSAT SAHİBİ FİRMA': 'ruhsat_sahibi_firma', 'RUHSAT NUMARASI': 'ruhsat_no', 'RUHSAT TARİHİ': 'ruhsat_tarihi'}
        df = pd.read_excel(filepath, sheet_name=sheet_name, header=1, dtype={'BARKOD': str, 'RUHSAT NUMARASI': str})
        
        df = df[list(column_map.keys())]
        df.rename(columns=column_map, inplace=True)
        df.dropna(how='all', inplace=True)
        
        processed_file_path = PROCESSED_DATA_DIR / output_filename
        df.to_json(processed_file_path, orient='records', lines=True, force_ascii=False)
        logging.info(f"-> Başarıyla '{output_filename}' olarak kaydedildi. ({len(df)} satır)")
        return True
    except Exception as e:
        logging.error(f"'{sheet_name}' işlenirken KRİTİK HATA: {e}")
        return False

def process_etkin_maddeler():
    """Etkin madde listesini işler (Başlık Satırı: 6)."""
    filename = "etkin_madde_listesi.xlsx"
    sheet_name = "Sheet1"
    output_filename = "etkin_maddeler.jsonl"

    filepath = RAW_DATA_DIR / filename
    if not filepath.exists():
        logging.warning(f"Kaynak dosya bulunamadı, atlanıyor: {filepath}")
        return True

    logging.info(f"'{filename}' -> '{sheet_name}' sayfası işleniyor...")
    try:
        column_map = {'Etkin Madde Adı': 'etkin_madde_adi', 'Sayı': 'basvuru_dosyasi_sayisi'}
        df = pd.read_excel(filepath, sheet_name=sheet_name, header=5, skipfooter=1)
        
        df = df[list(column_map.keys())]
        df.rename(columns=column_map, inplace=True)
        df.dropna(how='all', inplace=True)

        processed_file_path = PROCESSED_DATA_DIR / output_filename
        df.to_json(processed_file_path, orient='records', lines=True, force_ascii=False)
        logging.info(