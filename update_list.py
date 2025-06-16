# .github/workflows/update_checker.yml
name: TİTCK Güncelleme Kontrolü

on:
  schedule:
    - cron: '0 */6 * * *'      # Her 6 saatte bir
  workflow_dispatch: {}

permissions:
  issues: write
  contents: write

jobs:
  check-for-updates:
    runs-on: ubuntu-latest
    name: Kaynak Dosyaları Kontrol Et
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
        run: python -m pip install -r requirements.txt

      - name: Güncellemeleri Kontrol Et (download_list.py)
        id: checker
        run: python update_list.py

      - name: Değişiklik Varsa Bildirim Oluştur
        if: steps.checker.outcome == 'success' && steps.checker.conclusion == 'failure'
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: '📢 TİTCK Veri İndirici Hatası',
              body: 'update_list.py çalıştırılırken bir hata oluştu. Lütfen loglara bakın.'
            })

      - name: İndirilen Veriyi Depoya İşle
        run: |
          git config --global user.name 'github-actions[bot]'
          git config --global user.email 'github-actions[bot]@users.noreply.github.com'
          git add ham_veriler/
          if git diff --cached --quiet; then
            echo "Yeni veri yok."
          else
            git commit -m "Otomatik: Ham veriler güncellendi [$(date -u +'%Y-%m-%d')]"
            git push
          fi
