import pandas as pd
import google.generativeai as genai
from pathlib import Path
import json

# Temizlenmiş verilerin olduğu klasör
PROCESSED_DATA_DIR = Path("islenmis_veriler")

# Tüm .jsonl dosyalarını okuyup tek bir listede birleştir
all_data_rows = []
for file_path in PROCESSED_DATA_DIR.glob("*.jsonl"):
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            all_data_rows.append(json.loads(line))

# Liste'yi bir Pandas DataFrame'e çevir
df = pd.DataFrame(all_data_rows)

print(f"Toplam {len(df)} satır veri yüklendi.")

# Anlamsal bütünlük için her satırı tek bir metin bloğuna çevir (Chunking)
# Bu, arama yaparken AI'ın bağlamı daha iyi anlamasını sağlar.
def create_text_chunk(row):
    # Satırdaki tüm bilgileri anlamlı bir cümleye dönüştür
    chunk = []
    for col, value in row.items():
        if value is not None:
            chunk.append(f"{col.replace('_', ' ').title()}: {value}")
    return ". ".join(chunk)

df['text_chunk'] = df.apply(create_text_chunk, axis=1)

print("Veri parçaları (text chunks) oluşturuldu. Örnek:")
print(df['text_chunk'].iloc[0])