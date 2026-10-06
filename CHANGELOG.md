# Değişiklik Günlüğü

Bu dosya [Keep a Changelog](https://keepachangelog.com/tr/1.1.0/) biçimini izler ve proje
[Semantic Versioning](https://semver.org/lang/tr/) kullanır.

## [Yayınlanmadı]

### Eklendi
- **Hepsiburada adaptörü** (`adapters/hepsiburada.py`): sipariş, iade ve listeleme verisi için salt
  okunur HTTP istemcisi; Basic auth + mağaza kimliği taşıyan `User-Agent`, ISO 8601 tarih filtreleri,
  savunmacı alan eşlemesi (alan adı varyasyonları ve iç içe `data`/`listings` sarmalları).
- Adaptörler arasında paylaşılan `adapters/parsing.py` (para/tarih/sayı dönüşümleri) ve
  `adapters/http.py` (tek yerde 401/429/5xx politikası) — Trendyol adaptörü de bunları kullanıyor.
- **Yetenek bildirimi:** `MarketplaceAdapter.supports_reviews`. Hepsiburada satıcı API'sinde ürün
  yorumu uç noktası olmadığı için günlük özet yorum kuralını atlar ve bunu `notes` alanında
  ("not: ...") açıkça yazar — sessiz eksik metrik yok.
- Eşleme: Hepsiburada siparişlerinde `estimatedDeliveryEndDate` → `promised_delivery_at`, böylece
  teslim sözü ihlali kuralı bu pazaryerinde de çalışıyor.
- CLI: `--source hepsiburada`; `check` komutu iki pazaryerinin kimlik durumunu ve yorum okuma
  yeteneğini ayrı ayrı raporlar. `auto` sırası Trendyol → Hepsiburada → örnek veri.
- İngilizce README (`README.en.md`) ve iki dil arasında geçiş bağlantısı.
- 14 yeni test (toplam 84): Hepsiburada eşlemesi, durum sözlükleri, kimlik doğrulama başlığı,
  yeniden deneme davranışı, "yorum yok" notu ve ortak dönüşüm yardımcıları.

### Değişti
- `render_digest_text` sürüm numarasını artık `__version__` üzerinden okur (elle yazılmıyor).
- Trendyol adaptörünün taşıma/kimlik hatası mesajları ortak politika metnine taşındı.

### Planlanan
- Günlük özeti e-posta veya Slack webhook'una gönderme (v0.2.0).
- Hepsiburada adaptörünün canlı satıcı hesabıyla doğrulanması (uç nokta/alan adı sapmalarını görme).

## [0.1.0] - 2026-10-05

### Eklendi
- Sekiz salt okunur MCP aracı: `list_orders`, `list_returns`, `stock_alerts`, `sla_breaches`,
  `return_clusters`, `unanswered_reviews`, `price_overview`, `daily_digest`.
- Kural motoru: hazırlık/teslim SLA ihlalleri, stok uyarıları, fiyat tutarsızlıkları,
  iade nedeni kümeleri, cevapsız olumsuz yorumlar, iade oranı.
- Türkçe günlük aksiyon özeti üreticisi (`render_digest_text`) ve `trendyol-mcp demo` komutu.
- Fixture adaptörü ve anonim örnek veri seti (`examples/data`): kimlik bilgisi olmadan uçtan uca çalışır.
- Trendyol Marketplace Integration için salt okunur HTTP adaptörü (401/429/5xx yönetimi, yeniden deneme).
- `trendyol-mcp check | demo | tools | serve` komut satırı arayüzü.
- 60+ test: kural sınırları, HTTP eşlemesi (respx), CLI sözleşmesi ve stdio üzerinden MCP uçtan uca testi.
- GitHub Actions (Python 3.12/3.13 · ruff · mypy --strict · pytest · CLI smoke) ve Dependabot.
- Dokümantasyon: mimari, ADR'ler, kural sözlüğü, yol haritası ve SVG demo kaydı.
