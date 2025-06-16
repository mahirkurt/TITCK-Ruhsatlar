import sys
import logging
from pathlib import Path
import pandas as pd

# --- Loglama ve Klasör Kurulumu ---
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] - %(message)s",
                    stream=sys.stdout)
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
    df.to_json(processed_file_path,
               orient='records',
               lines=True,
               force_ascii=False)
    logging.info(f"-> '{original_filename}' başarıyla '{output_filename}' olarak kaydedildi. ({len(df)} satır)")


def process_generic_file(filename, sheet_name, output_filename,
                         header_row, column_map, dtype=None,
                         skip_footer=0):
    """Ortak Excel işleme ve JSONL kaydetme adımlarını gerçekleştirir."""
    filepath = get_file_path(filename)
    if not filepath:
        return True

    logging.info(f"'{filename}' -> '{sheet_name}' sayfası işleniyor...")
    try:
        read_args = {
            "sheet_name": sheet_name,
            "header": header_row,
            "dtype": dtype
        }
        if skip_footer:
            read_args["skipfooter"] = skip_footer
            read_args["engine"] = "python"

        df = pd.read_excel(filepath, **read_args)
        existing_cols = [col for col in column_map if col in df.columns]
        if not existing_cols:
            logging.error(
                f"'{sheet_name}' sayfasında beklenen sütunlardan hiçbiri bulunamadı.")
            return False

        df = df[existing_cols]
        df.rename(columns=column_map, inplace=True)
        df.dropna(how='all', inplace=True)

        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].str.strip()

        save_as_jsonl(df, output_filename, filename)
        return True
    except Exception as e:
        logging.error(
            f"'{sheet_name}' işlenirken KRİTİK HATA: {e}",
            exc_info=True)
        return False

# ======================================================================
# İŞLEYİCİ FONKSİYONLAR
# ======================================================================

def process_ilac_fiyat_listesi():
    """İlaç fiyat listesi dosyasını işler."""
    filename = "ilac_fiyat_listesi.xlsx"
    filepath = get_file_path(filename)
    if not filepath:
        return True

    sheet_name = "REFERANS BAZLI İLAÇ LİSTESİ"
    logging.info(f"'{filename}' -> '{sheet_name}' sayfası işleniyor...")

    column_map = {
        'İLAÇ ADI': 'ilac_adi',
        'FİRMA ADI': 'firma_adi',
        'GERÇEK KAYNAK FİYAT': 'gercek_kaynak_fiyat'
    }
    try:
        df = pd.read_excel(filepath,
                           sheet_name=sheet_name,
                           header=1,
                           dtype=str)
        df = df[[col for col in column_map if col in df.columns]]
        df.rename(columns=column_map, inplace=True)
        df.dropna(how='all', inplace=True)
        save_as_jsonl(df, "ilac_fiyatlari.jsonl", filename)
        return True
    except Exception as e:
        logging.error(
            f"'{sheet_name}' işlenirken KRİTİK HATA: {e}",
            exc_info=True)
        return False


def process_ruhsatli_urunler():
    """Ruhsatlı ürünler listesini işler ve ruhsat durum kodlarını metne çevirir."""
    column_map = {
        'BARKOD': 'barkod',
        'ÜRÜN ADI': 'urun_adi',
        'ETKİN MADDE': 'etkin_madde',
        'ATC KODU': 'atc_kodu',
        'RUHSAT SAHİBİ FİRMA': 'ruhsat_sahibi_firma',
        'RUHSAT NUMARASI': 'ruhsat_no',
        'RUHSAT TARİHİ': 'ruhsat_tarihi',
        'RUHSATI ASKIDA OLMAYAN ÜRÜN': 'ruhsat_durumu',
        'ASKIYA ALINMA TARİHİ': 'askiya_alinma_tarihi'
    }
    filepath = get_file_path("ruhsatli_ilaclar_listesi.xlsx")
    if not filepath:
        return True

    try:
        df = pd.read_excel(
            filepath,
            sheet_name="RUHSATLI ÜRÜNLER LİSTESİ",
            header=5,
            dtype={'BARKOD': str, 'RUHSAT NUMARASI': str}
        )
        df = df[[col for col in column_map if col in df.columns]]
        df.rename(columns=column_map, inplace=True)
        df.dropna(how='all', inplace=True)

        ruhsat_map = {
            0: 'RUHSAT GEÇERLİ',
            1: 'MADDE-23 GEREKÇELİ ASKIDA',
            2: 'FARMAKOVİJİLANS GEREKÇELİ ASKIDA',
            3: 'MADDE-22 GEREKÇELİ ASKIDA'
        }
        if 'ruhsat_durumu' in df.columns:
            df['ruhsat_durumu'] = df['ruhsat_durumu'].map(ruhsat_map).fillna('Bilinmeyen Durum Kodu')

        save_as_jsonl(df, "ruhsatli_urunler.jsonl", "ruhsatli_ilaclar_listesi.xlsx")
        return True
    except Exception as e:
        logging.error(
            f"'RUHSATLI ÜRÜNLER LİSTESİ' işlenirken KRİTİK HATA: {e}",
            exc_info=True)
        return False


def process_etkin_maddeler():
    """Etkin madde listesi dosyasını işler."""
    column_map = {
        'ETKİN MADDE': 'etkin_madde_adi',
        'KODU': 'basvuru_dosyasi_sayisi'
    }
    return process_generic_file(
        "etkin_madde_listesi.xlsx",
        "Sheet1",
        "etkin_maddeler.jsonl",
        5,
        column_map,
        skip_footer=1
    )


def process_skrs_aktif_urunler():
    """SKRS aktif ürünler listesi dosyasını işler."""
    column_map = {
        'İLAÇ ADI': 'urun_adi',
        'BARKOD': 'barkod',
        'ATC KODU': 'atc_kodu',
        'ATC ADI': 'atc_adi',
        'FİRMA ADI': 'firma_adi',
        'REÇETE TÜRÜ': 'recete_turu',
        'TEMEL İLAÇ LİSTESİ DURUMU': 'temel_ilac_listesi_durumu',
        'ÇOCUK TEMEL İLAÇ LİSTESİ DURUMU': 'cocuk_temel_ilac_listesi_durumu',
        'YENİDOĞAN TEMEL İLAÇ LİSTESİ DURUMU': 'yenidogan_temel_ilac_listesi_durumu',
        'AKTİF ÜRÜNLER LİSTESİNE ALINDIĞI TARİH': 'listeye_alinma_tarihi'
    }
    return process_generic_file(
        "skrs_erecete_listesi.xlsx",
        "AKTİF ÜRÜNLER LİSTESİ",
        "skrs_aktif_urunler.jsonl",
        2,
        column_map,
        dtype={'BARKOD': str}
    )


def process_skrs_pasif_urunler():
    """SKRS pasif ürünler listesi dosyasını işler."""
    column_map = {
        'İLAÇ ADI': 'urun_adi',
        'BARKOD': 'barkod',
        'ATC KODU': 'atc_kodu',
        'ATC ADI': 'atc_adi',
        'FİRMA ADI': 'firma_adi',
        'REÇETE TÜRÜ': 'recete_turu',
        'PASİF ÜRÜNLER LİSTESİNE ALINDIĞI TARİH': 'listeye_alinma_tarihi'
    }
    return process_generic_file(
        "skrs_erecete_listesi.xlsx",
        "PASİF ÜRÜNLER LİSTESİ",
        "skrs_pasif_urunler.jsonl",
        2,
        column_map,
        dtype={'BARKOD': str}
    )


def process_yurtdisi_etkin_maddeler():
    """Yurtdışı etkin madde listesi dosyasını işler."""
    column_map = {
        'ETKİN MADDE ADI': 'etkin_madde',
        'HASTALIK/TANI': 'hastalik_tani',
        'KISITLAMA': 'kisitlama'
    }
    return process_generic_file(
        "yurtdisi_etkin_madde_listesi.xlsx",
        "YD-ETKIN MADDE LISTESI",
        "yurtdisi_etkin_maddeler.jsonl",
        1,
        column_map
    )


def main():
    """Tüm veri temizleme işlemlerini yürüten ana fonksiyon."""
    logging.info("===== Veri Temizleme ve Standardizasyon Başlatıldı =====")
    functions = [
        process_ilac_fiyat_listesi,
        process_ruhsatli_urunler,
        process_etkin_maddeler,
        process_skrs_aktif_urunler,
        process_skrs_pasif_urunler,
        process_yurtdisi_etkin_maddeler
    ]
    results = [fn() for fn in functions]
    if all(results):
        logging.info("===== Tüm Dosyalar Başarıyla İşlendi =====")
    else:
        logging.error(
            "!!! Bazı dosyalar işlenirken hatalar oluştu. Lütfen logları kontrol edin. !!!"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
