# .github/workflows/update_list.yml
name: TİTCK Ham Veri Güncelleme

on:
  workflow_dispatch: {}
  schedule:
    # Her gün UTC 04:00’te (Türkiye saatiyle 07:00) çalışsın
    - cron: '0 4 * * *'

permissions:
  contents: write

jobs:
  download-raw-data:
    runs-on: ubuntu-latest
    name: Ham Verileri İndir
    steps:
      - name: Depoyu Klonla
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Python Kurulumu
        uses: actions/setup-python@v5
        with:
          python-version: '3.9'

      - name: Bağımlılıkları Yükle
        run: python -m pip install --upgrade pip && pip install -r requirements.txt

      - name: Ham Veriyi İndir (update_list.py)
        run: python update_list.py

      - name: İndirilen Veriyi Depoya Ekle ve Commit
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add ham_veriler/
          if git diff --cached --quiet; then
            echo "Yeni veri yok, commit skippable."
          else
            git commit -m "Otomatik: Ham veriler güncellendi [$(date -u +'%Y-%m-%d')]"
            git push
          fi
