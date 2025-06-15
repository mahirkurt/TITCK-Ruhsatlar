# Dosya Adı: diagnose_excel.py

import pandas as pd
import sys
from pathlib import Path

def inspect_excel(filepath_str):
    """Bir Excel dosyasının yapısını inceler ve ilk 10 satırını yazdırır."""
    filepath = Path(filepath_str)
    if not filepath.exists():
        print(f"HATA: Dosya bulunamadı: {filepath}")
        return

    print(f"--- Dosya İnceleniyor: {filepath.name} ---")
    try:
        # Dosyadaki tüm sayfa adlarını al
        xls = pd.ExcelFile(filepath)
        sheet_names = xls.sheet_names
        print(f"Bulunan Sayfalar: {sheet_names}")

        # Her sayfanın ilk 10 satırını ham olarak oku ve yazdır
        for sheet in sheet_names:
            print(f"\n--- Sayfa Adı: {sheet} ---")
            # header=None parametresi, dosyanın ham halini görmemizi sağlar
            df_raw = pd.read_excel(filepath, sheet_name=sheet, header=None)
            print("Dosyanın ilk 10 satırı:")
            print(df_raw.head(10).to_string())
            print("-" * (len(sheet) + 12))

    except Exception as e:
        print(f"Dosya incelenirken bir hata oluştu: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        inspect_excel(sys.argv[1])
    else:
        print("Lütfen incelenecek dosyanın yolunu argüman olarak belirtin.")