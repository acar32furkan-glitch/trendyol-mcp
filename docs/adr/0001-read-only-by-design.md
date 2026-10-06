# ADR-0001 — Salt okunur tasarım

- **Durum:** Kabul edildi
- **Tarih:** 2026-10-05
- **Karar verenler:** proje sürdürücüsü

## Bağlam

Bir ajan, satıcının kendi pazaryeri hesabına bağlanıyor. Ajanlar yanlış karar verebilir, yanlış
argümanla araç çağırabilir veya bir hata zinciri istenmeyen yazma işlemine dönüşebilir. Fiyatı
yanlış güncelleyen veya sipariş iptal eden bir otomasyon, satıcı için doğrudan gelir kaybıdır.
Ayrıca pazaryeri sözleşmeleri otomatik değişiklik yapan üçüncü taraf araçlara karşı hassastır.

## Karar

`MarketplaceAdapter` protokolü **yalnızca okuma** metotları içerir (`list_orders`, `list_returns`,
`list_products`, `list_reviews`). Hiçbir adaptör, araç veya komut `POST`/`PUT`/`PATCH`/`DELETE`
isteği göndermez. MCP araçları `read_only_hint=true`, `destructive_hint=false` olarak işaretlenir.

## Sonuçlar

**Olumlu**
- Yanlış kullanımda bile satıcı hesabında değişiklik yapılamaz — hata maliyeti asimetrik olarak düşer.
- Pazaryeri sözleşmelerine uyum ve kurumsal satıcılar için güvenilir bir anlatı.
- Kapsam küçük kalır: test edilmesi gereken yüzey okuma + hesaplama.

**Olumsuz**
- "Ürünü o da düzeltsin" beklentisi karşılanmaz; ürün öneri listesi üretir, uygulamayı insana bırakır.
- Yazma ihtiyacı doğduğunda ayrı bir ürün/mimari kararı gerekir (bu ADR'yi değiştirmek tek satırla olmaz).

## Alternatifler

1. **Yazma yetkisiyle birlikte onay akışı:** iki aşamalı onay (ajan önerir, insan uygular) hâlâ risk
   taşıyor ve asıl değer olan "sabah raporu" için gerekmiyor.
2. **Panel otomasyonu (tarayıcı) ile yazma:** resmî olmayan yol, kırılgan ve sözleşme riski yüksek.
