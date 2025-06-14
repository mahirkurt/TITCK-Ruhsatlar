# -*- coding: utf-8 -*-
"""
Bu betik, TİTCK'dan indirilen çeşitli ham Excel dosyalarını okur,
temel temizlik yapar ve yapay zeka modellerinin kullanabileceği
temiz .jsonl formatında kaydeder.

BASİTLEŞTİRİLMİŞ NİHAİ SÜRÜM
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


def main():
    """Tüm veri temizleme işlemlerini yürüten ana fonksiyon."""
    logging.info("===== Veri Temizleme ve Standardizasyon Başlatıldı =====")
    
    # İşlenecek dosyaların konfigürasyon listesi
    files_to_process = [
        {
            "input_filename": "ruhsatli_ilaclar_listesi.xlsx",
            "sheet_name": "RUHSATLI ÜRÜNLER LİSTESİ",
            "output_filename": "ruhsatli_urunler.jsonl",
            "header_row": 1, # Başlıklar 2. satırda
            "column_map": {'BARKOD': 'barkod', 'ÜRÜN ADI': 'urun_adi', 'ETKİN MADDE': 'etkin_madde', 'ATC KODU': 'atc_kodu', 'RUHSAT SAHİBİ FİRMA': 'ruhsat_sahibi_firma'}
        },
        {
            "input_filename": "etkin_madde_listesi.xlsx",
            "sheet_name": "Sheet1",
            "output_filename": "etkin_maddeler.jsonl",
            "header_row": 5, # Başlıklar 6. satırda
            "column_map": {'Etkin Madde Adı': 'etkin_madde_adi', 'Sayı': 'basvuru_dosyasi_sayisi'}
        },
        {
            "input_filename": "yurtdisi_etkin_madde_listesi.xlsx",
            "sheet_name": "YD-Etkin madde listesi",
            "output_filename": "yurtdisi_etkin_maddeler.jsonl",
            "header_row": 1, # Başlıklar 2. satırda
            "column_map": {'Etkin Madde': 'etkin_madde', 'Farmasötik Form': 'farmas
