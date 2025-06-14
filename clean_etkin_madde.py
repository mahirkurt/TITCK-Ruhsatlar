# -*- coding: utf-8 -*-
import pandas as pd; from pathlib import Path; import logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
RAW_DATA_DIR = Path("ham_veriler")
PROCESSED_DATA_DIR = Path("islenmis_veriler")
PROCESSED_DATA_DIR.mkdir(exist_ok=True)

logging.info("-> 'etkin_madde_listesi.xlsx' işleniyor...")
filepath = RAW_DATA_DIR / "etkin_madde_listesi.xlsx"
if filepath.exists():
    try:
        column_map = {'Etkin Madde Adı': 'etkin_madde_adi', 'Sayı': 'basvuru_dosyasi_sayisi'}
        df = pd.read_excel(filepath, sheet_name="Sheet1", header=5, skipfooter=1)
        df = df[list(column_map.keys())]
        df.rename(columns=column_map, inplace=True)
        df.dropna(how='all', inplace=True)
        df.to_json(PROCESSED_DATA_DIR / "etkin_maddeler.jsonl", orient='records', lines=True, force_ascii=False)
        logging.info("   -> Başarılı.")
    except Exception as e:
        logging.error(f"   -> HATA: {e}")
else:
    logging.warning("   -> Dosya bulunamadı, atlanıyor.")