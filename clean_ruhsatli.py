# -*- coding: utf-8 -*-
import pandas as pd; from pathlib import Path; import logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
RAW_DATA_DIR = Path("ham_veriler")
PROCESSED_DATA_DIR = Path("islenmis_veriler")
PROCESSED_DATA_DIR.mkdir(exist_ok=True)

logging.info("-> 'ruhsatli_ilaclar_listesi.xlsx' işleniyor...")
filepath = RAW_DATA_DIR / "ruhsatli_ilaclar_listesi.xlsx"
if filepath.exists():
    try:
        column_map = {'BARKOD': 'barkod', 'ÜRÜN ADI': 'urun_adi', 'ETKİN MADDE': 'etkin_madde', 'ATC KODU': 'atc_kodu', 'RUHSAT SAHİBİ FİRMA': 'ruhsat_sahibi_firma'}
        df = pd.read_excel(filepath, sheet_name="RUHSATLI ÜRÜNLER LİSTESİ", header=1, dtype={'BARKOD': str})
        df = df[list(column_map.keys())]
        df.rename(columns=column_map, inplace=True)
        df.dropna(how='all', inplace=True)
        df.to_json(PROCESSED_DATA_DIR / "ruhsatli_urunler.jsonl", orient='records', lines=True, force_ascii=False)
        logging.info("   -> Başarılı.")
    except Exception as e:
        logging.error(f"   -> HATA: {e}")
else:
    logging.warning("   -> Dosya bulunamadı, atlanıyor.")