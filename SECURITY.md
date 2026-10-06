# Güvenlik Politikası

## Desteklenen sürümler

| Sürüm | Destek |
|-------|--------|
| 0.1.x | ✅ |
| < 0.1 | ❌ (geliştirme sürümleri) |

## Bir açığı nasıl bildirirsiniz?

Güvenlikle ilgili konuları **herkese açık issue olarak açmayın.** Bunun yerine depo sahibine
GitHub üzerinden özel mesaj gönderin (acar32furkan-glitch) ve şunları ekleyin:

- Etkilenen sürüm ve komut/araç,
- Yeniden üretme adımları (mümkünse örnek veri ile),
- Etki değerlendirmesi: hangi veri okunabilir, hangi sınır aşılabilir.

İlk yanıt hedefi 72 saattir.

## Tasarımla gelen güvenlik sınırları

- **Salt okunur:** hiçbir adaptör veya araç `POST`/`PUT`/`PATCH`/`DELETE` isteği göndermez; satıcı
  hesabında değişiklik yapamaz (`docs/adr/0001-read-only-by-design.md`).
- **Kimlik bilgisi yalnızca ortam değişkeninde:** `TRENDYOL_API_KEY`, `TRENDYOL_API_SECRET`,
  `TRENDYOL_SUPPLIER_ID`. Anahtarlar loglanmaz, hata mesajlarına yazılmaz ve depoda tutulmaz
  (`.env` git'e girmez; `pre-commit` içinde `detect-private-key` çalışır).
- **Ağ çıkışı yalnızca pazaryeri API'si:** `TRENDYOL_BASE_URL` dışında adres çağrılmaz.
- **Örnek veri anonimdir:** `examples/data` içinde gerçek müşteri/sipariş bilgisi yoktur.

## Kapsam dışı

- Trendyol'un kendi API'sindeki zafiyetler (Trendyol'a bildirilmelidir).
- Kullanıcının kendi makinesindeki yanlış yapılandırmalar (ör. anahtarı komut satırına yazmak).
- Sosyal mühendislik senaryoları.
