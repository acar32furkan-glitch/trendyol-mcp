# Yol Haritası

Her sürüm tek bir soruya cevap verir. **Yazma yetkisi hiçbir sürümde planlanmıyor** (bkz. ADR-0001);
ürün "okuyup uyaran nöbetçi" olarak kalacak.

## v0.1.0 — Çalışan çekirdek (yayınlandı, 2026-10-05)
- 8 salt okunur MCP aracı, 9 kural, Türkçe günlük özet.
- Kimlik bilgisi olmadan çalışan örnek veri seti ve uçtan uca stdio testi.

## v0.2.0 — İkinci pazaryeri + rapor dağıtımı
- ✅ `adapters/hepsiburada.py` (salt okunur) — sipariş, iade ve listeleme verisi; ortak sözleşmenin
  ikinci uygulaması. **Kalan iş:** gerçek satıcı hesabıyla canlı doğrulama (uç nokta/alan adı sapması
  çıkarsa yalnızca alan tercih listeleri güncellenir).
- Günlük özeti e-posta/Slack webhook'una gönderen `trendyol-mcp report --to ...` komutu.
- Örnek veride ikinci pazaryeri senaryoları (çok kanallı stok çakışması): aynı ürünün iki
  pazaryerindeki stokunu karşılaştırma.

## v0.3.0 — Zamanlanmış çalışma + hafif panel
- `trendyol-mcp watch --at 09:00` (yerelde zamanlayıcı) ve Docker imajı.
- Bulgu geçmişini saklama (SQLite) → "bu sorun kaç gündür var?" sorusu.
- Statik HTML rapor (tek dosya, e-posta eki olarak gönderilebilir).

## v1.0.0 — Ekip kullanımı
- Çoklu mağaza profili ve kimlik bilgisi için işletim sistemi anahtar zinciri (OS keyring) desteği.
- Kural paketleri: kural setini YAML ile tanımlama (kod yazmadan eşik/kural seçimi).
- Kararlı API sözleşmesi ve sürüm uyumluluk politikası.

## Kapsam dışı (bilinçli)
- Pazaryeri paneline **yazma** (fiyat güncelleme, sipariş iptali, kargo etiketi).
- Resmî olmayan kazıma yöntemleriyle panelden veri çekme.
- Kullanıcı yönetimi/çok kiracılı SaaS altyapısı.
