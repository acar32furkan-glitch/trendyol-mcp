# Kural Sözlüğü

Tüm eşikler `Thresholds` üzerinden geçer (`tools.py` / `build_digest`). Bulgu metinleri Türkçe ve
eylem odaklıdır: **ne oldu → hangi kayıt → bugün ne yapılmalı**.

| Kod | Kural | Önem | Eşik (varsayılan) | Tipik mesaj |
|-----|-------|------|-------------------|-------------|
| `HAZIRLIK_GECIKTI` | Sipariş 48 saatten uzun süredir `created`/`picking` durumunda | 48-72 saat: UYARI · 72 saat+: KRİTİK | `--sla-hours 48` | "Sipariş 80 saattir hazırlanmayı bekliyor (eşik: 48 saat)." |
| `TESLIM_GECIKTI` | Açık siparişin söz verilen teslim tarihi geçmiş | KRİTİK | `promised_delivery_at` | "Söz verilen teslim tarihi 15 saat önce geçti." |
| `STOK_YOK` | Ürün stoğu 0 | KRİTİK | `--low-stock 5` | "P-3001 barkodlu üründe stok tükendi (eşik: 5)." |
| `STOK_AZ` | Stok eşiğin altında (0 hariç) | UYARI | `--low-stock 5` | "P-3002 barkodlu üründe stok 3 adede düştü (eşik: 5)." |
| `IADE_KUMESI` | Son N günde aynı iade nedeni ≥ 3 kez | 3-5: UYARI · 6+: KRİTİK | `--return-cluster-min 3` | "Son 30 günde 3 iade aynı nedeni gösteriyor; toplam iade tutarı 1251.40 TL." |
| `YORUM_CEVAPSIZ` | 1-2 yıldızlı yorum 24 saatten uzun süredir yanıtsız | 1 yıldız veya ≥3 yorum: KRİTİK · diğer: UYARI | `--review-hours 24` | "“Rengi fotoğraftakinden çok farklı çıktı” · 03.10.2026 tarihinde geldi, hâlâ cevap yok." |
| `FIYAT_LISTEDEN_YUKSEK` | Satış fiyatı liste fiyatından yüksek | UYARI | — | "Satış fiyatı 249.90 TL, liste fiyatı 199.90 TL." |
| `INDIRIM_ANORMAL` | İndirim oranı ≥ %70 (eksik haneli fiyat şüphesi) | UYARI | `DISCOUNT_ANOMALY_RATIO` | "Liste 189.90 TL → satış 39.90 TL." |
| `IADE_ORANI` | Son 30 günün iade oranı (bilgi amaçlı) | BİLGİ | — | "Son 30 günün iade oranı: %41.7" |

## Önem sırası

`critical > warning > info`. Aynı önem düzeyinde bulgular `code` ve başlığa göre alfabetik sıralanır
— böylece çıktı deterministiktir ve testlerde birebir karşılaştırılabilir (`tests/test_digest.py`).

## Neden bu eşikler?

- **48 saatlik hazırlık penceresi:** TR pazaryerlerinde kargo teslim süresi baskısının başladığı tipik nokta.
- **24 saatlik yorum yanıtı:** olumsuz yorumun satın alma kararına etkisini sınırlayan kabul edilebilir süre.
- **%70 indirim anomalisi:** eksik haneli fiyat girişinin (189.90 → 18.99/39.90) tipik aralığı.
- **3 tekrarlı iade nedeni:** tek olay gürültü, üç olay eğilim.

Eşikler sabit değildir: `Thresholds` üzerinden kendi işletmenize göre ayarlanabilir ve testlerde
parametre olarak değiştirilerek davranış doğrulanabilir.

## Bulgu şeması

```json
{
  "severity": "critical",
  "severity_tr": "KRİTİK",
  "code": "TESLIM_GECIKTI",
  "title_tr": "Teslim sözü geçti: TY-1003",
  "detail_tr": "trendyol · Müşteri C · durum: kargoda. Söz verilen teslim tarihi 15 saat önce geçti.",
  "action_tr": "Kargo firmasıyla iletişime geçin ve müşteriye bilgi mesajı gönderin.",
  "references": ["TY-1003"]
}
```
