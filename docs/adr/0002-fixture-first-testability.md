# ADR-0002 — Örnek veri adaptörü birinci sınıf vatandaş

- **Durum:** Kabul edildi
- **Tarih:** 2026-10-05

## Bağlam

Projenin değerini göstermek için gerçek satıcı verisi gerekiyor; ama gerçek veri (a) Gizlilik nedeniyle
depoya konamaz, (b) Değerlendiren kişide kimlik bilgisi yoktur, (c) Zamanla değiştiği için testleri
kırılgan yapar. "Sadece kendi hesabınızla çalışır" diyen bir araç, GitHub'da kimse tarafından
çalıştırılamaz ve doğrulanamaz.

## Karar

`FixtureAdapter`, `TrendyolAdapter` ile aynı protokolü uygulayan gerçek bir adaptördür. Depoda
anonimleştirilmiş bir veri seti (`examples/data`) bulunur ve bu set **kendi zaman çapasını taşır**
(`meta.json` → `reference_time`). Sunucu, kimlik bilgisi yoksa otomatik olarak bu adaptöre düşer
(`--source auto`).

Kural fonksiyonları zamanı parametre olarak alır; demo ve testler bu çapaya göre çalışır.

## Sonuçlar

**Olumlu**
- `git clone` + `uv run trendyol-mcp demo` ile sunucu kimlik bilgisi olmadan uçtan uca çalışır.
- Testler deterministik: tarih bağımlı hiçbir test yok (bkz. `tests/test_digest.py` çıktı karşılaştırması).
- Yeni bir pazaryeri adaptörü, aynı örnek veri setiyle karşılaştırmalı test edilebilir.
- Katkı veren, gerçek veriye ihtiyaç duymadan kural geliştirebilir.

**Olumsuz**
- Örnek veri bakımı gerçek bir iştir; kural eklendiğinde senaryo eklemek gerekir (bu bilinçli bir maliyet).
- Demo çıktısı "gerçek" veri değildir; bu yüzden her çıktıda kaynak adı (`fixture`) gösterilir.

## Alternatifler

1. **Gerçek veri isteyen zorunlu kurulum:** değerlendirme bariyeri; GitHub üzerinden doğrulanamaz.
2. **Kayıtlı (recorded) HTTP yanıtları:** gerçek veri sızma riski taşır ve okunabilirliği düşürür.
   Bunun yerine HTTP katmanı `respx` ile test edilir (bkz. `tests/test_trendyol_adapter.py`).
