# Değişiklik Günlüğü

Bu dosya [Keep a Changelog](https://keepachangelog.com/tr/1.1.0/) biçimini izler ve proje
[Semantic Versioning](https://semver.org/lang/tr/) kullanır.

## [Yayınlanmadı]

### Planlanan
- Hepsiburada adaptörü (salt okunur).
- Günlük özeti e-posta veya Slack webhook'una gönderme.

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
