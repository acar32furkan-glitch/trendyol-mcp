# Sorun Giderme

**Belirti → neden → çözüm.** Buradaki her çıktı gerçekten çalıştırılmış komutlardan alınmıştır;
uydurma çıktı yoktur. Canlı bir satıcı hesabı gerektiren HTTP senaryoları (401/403/429/boş yanıt),
tüm isteklere istenen durum kodunu döndüren yerel bir sahte sunucuya `TRENDYOL_BASE_URL` /
`HEPSIBURADA_ORDERS_BASE_URL` yönlendirilerek üretildi (tarif: [belgenin sonu](#ek-http-senaryolarını-yerelde-yeniden-üretme)).
Aynı yollar `respx` ile taklit edilmiş yanıtlarla `tests/test_trendyol_adapter.py` içinde de sabitlenmiştir.

## Önce ortamı görün

Her şeyden önce şunu çalıştırın; hangi kaynağın seçildiğini ve kaç kayıt okunduğunu söyler:

```console
$ uv run trendyol-mcp check
trendyol-mcp 0.1.0
  aktif kaynak      : fixture
  canlı kimlik      : yok (fixture kaynağı kullanılıyor)
  kimlik bilgileri  : trendyol yok, hepsiburada yok
  yorum okuma       : destekli
  örnek veri        : C:\Users\admin\projects\trendyol-mcp\examples\data
  değerlendirme anı : 2026-10-05T09:00:00+03:00
  kayıtlar          : siparis 12, iade 5, urun 8, yorum 6
  durum             : hazır ✔ (bir ajan bağlayabilirsiniz: trendyol-mcp serve)
```

`kayıtlar` satırı 0/0/0/0 ise sorun kimlik bilgisinde ya da tarih penceresindedir (aşağıya bakın),
kural motorunda değil.

## Hızlı bakış

| Belirti | Neden | Çözüm |
|---------|-------|-------|
| `hata: Trendyol kimlik bilgileri yok…` | `--source trendyol` verildi ama ortam değişkenleri eksik | Üçünü de tanımlayın ya da `--source auto`/`fixture` kullanın → [1](#1-eksik-kimlik-bilgisi) |
| `hata: Kimlik bilgileri reddedildi (HTTP 401)…` | Anahtar/şifre çifti yanlış (veya rotate edilmiş) | Panelden üretilen değerleri yenileyin → [2](#2-http-401--kimlik-bilgisi-reddedildi) |
| `hata: … isteği başarısız: HTTP 403` | Yetki yok: uç nokta izni, satıcı kimliği uyuşmazlığı veya IP kısıtı | Satıcı kimliğini ve uç nokta iznini doğrulayın → [3](#3-http-403--yetki-yok) |
| `hata: … 3 denemede başarısız oldu: … HTTP 429` | Hız sınırı (rate limit) | Bekleyin, tarih penceresini/liste boyunu daraltın → [4](#4-http-429--hız-sınırı) |
| `Bulgu: 0 … Bugün aksiyon gerektiren bir şey yok.` | Okunacak kayıt yok ya da gerçekten sorun yok | Hata değildir; `check` ile kayıt sayılarını doğrulayın → [5](#5-boş-veri-bulgu-yok) |
| `not: … ürün yorumlarını okumaya izin vermiyor…` | Uç nokta yok (Hepsiburada yorumları) | Beklenen davranış; `not:` satırı bunu bildirir → [6](#6-uç-nokta-yok-not-satırı) |
| `hata: Fixture dosyası yok…` / `şemaya uymuyor…` | Örnek veri klasörü bozuk/eksik | `--fixtures` yolunu ve dosyaları düzeltin → [7](#7-örnek-veri-bozuk-veya-eksik) |

---

## 1) Eksik kimlik bilgisi

**Belirti**

```console
$ trendyol-mcp --source trendyol check
hata: Trendyol kimlik bilgileri yok. TRENDYOL_SUPPLIER_ID, TRENDYOL_API_KEY ve TRENDYOL_API_SECRET ortam değişkenlerini tanımlayın ya da `--source fixture` kullanın.
$ echo $?
1
```

**Neden.** `--source trendyol` açıkça Trendyol'u seçer ve adaptör kimlik bilgisi olmadan
kurulamaz. Değişkenlerin **yalnızca biri** eksikse bile durum "kimlik yok" sayılır: `from_env`
üçünün de dolu olmasını şart koşar (boşlukla verilmiş değer boş kabul edilir).

**Çözüm.** Üçünü birlikte tanımlayın (örn. `.env`), ya da hangisi varsa onu kendiliğinden seçen
`--source auto` ile devam edin. Hiç kimlik bilgisi yoksa sunucu örnek veri setine düşer ve bu
`check` çıktısında `aktif kaynak : fixture` olarak görünür — sessizce canlı veri taklit etmez.

## 2) HTTP 401 — kimlik bilgisi reddedildi

**Belirti**

```console
$ TRENDYOL_SUPPLIER_ID=123 TRENDYOL_API_KEY=dummy TRENDYOL_API_SECRET=dummy \
    TRENDYOL_BASE_URL=http://127.0.0.1:8787 trendyol-mcp --source trendyol check
hata: Kimlik bilgileri reddedildi (HTTP 401). Sağlayıcı panelinden üretilen anahtar/şifre değerlerini kontrol edin.
$ echo $?
1
```

**Neden.** İstek sunucuya ulaştı ama kimlik doğrulanamadı: anahtar/şifre çifti yanlış, süresi
dolmuş veya panelde yeniden üretilip burada güncellenmemiş. Aynı hatayı `--source hepsiburada`
tarafında da alırsınız.

**Çözüm.** Panelden yeni bir anahtar/şifre çifti üretip ortam değişkenlerini güncelleyin.
401 için ayrı bir dal vardır ve bu mesajda **anahtar değeri asla yer almaz** (bkz. `SECURITY.md`);
log dosyalarını paylaşırken sızıntı riski yoktur. Beklenen davranış
`tests/test_trendyol_adapter.py::test_unauthorized_raises_a_clear_error` ile sabitlenmiştir.

## 3) HTTP 403 — yetki yok

**Belirti**

```console
$ TRENDYOL_SUPPLIER_ID=123 TRENDYOL_API_KEY=dummy TRENDYOL_API_SECRET=dummy \
    TRENDYOL_BASE_URL=http://127.0.0.1:8788 trendyol-mcp --source trendyol check
hata: /integration/order/sellers/123/orders isteği başarısız: HTTP 403
$ echo $?
1
```

**Neden.** 401'den farklı olarak kimlik **doğrulandı** ama bu işleme izin yok. Tipik üç kaynak:
(1) token'ın o uç nokta için okuma izni yok, (2) URL'deki satıcı kimliği (`123`) token'ın sahibi
olan satıcıyla uyuşmuyor, (3) uç nokta yalnızca panelde tanımlı IP adreslerinden çağrılabiliyor.

**Çözüm.** `TRENDYOL_SUPPLIER_ID` değerini panelde gördüğünüz satıcı kimliğiyle karşılaştırın;
entegrasyon kullanıcısına ilgili uç noktanın okuma iznini verin; IP kısıtı varsa çalıştırdığınız
makinenin çıkış IP'sini izin listesine ekleyin. Kod 403'ü 401 ile **bilinçli olarak karıştırmaz**:
mesaj farklıdır çünkü yapılacak iş de farklıdır (anahtar değil, izin).

## 4) HTTP 429 — hız sınırı

**Belirti**

```console
$ time TRENDYOL_SUPPLIER_ID=123 TRENDYOL_API_KEY=dummy TRENDYOL_API_SECRET=dummy \
    TRENDYOL_BASE_URL=http://127.0.0.1:8789 trendyol-mcp --source trendyol check
hata: /integration/order/sellers/123/orders isteği 3 denemede başarısız oldu: /integration/order/sellers/123/orders geçici hata döndürdü: HTTP 429

real    0m3,081s
$ echo $?
1
```

**Neden.** Sağlayıcı kısa sürede çok istek gördü. 429 (ve 500/502/503/504) **geçici** sayılır.

**Çözüm.** İstemci bu kodlarda üstel geri çekilmeyle (0.5 sn, sonra 1 sn) üç kez dener; ~3 saniyede
hâlâ 429 alıyorsanız beklemek dışında yapılacak şey istek hacmini düşürmektir: `--now`/`since` ile
tarih penceresini daraltın, `limit` değerini küçültün, aynı anda ikinci bir kopyayı çalıştırmayın.
Sürekli 429, sınırı **kalıcı** aştığınızı gösterir ve yeniden deneme döngüsünü uzatmak çözmez.

## 5) Boş veri (bulgu yok)

**Belirti.** Komut başarılı biter (kod 0), özet sıfır bulgu gösterir:

```console
$ trendyol-mcp --source trendyol demo
GÜNLÜK SATICI ÖZETİ — 06.10.2026 16:08
Kaynak: trendyol  ·  Kural motoru: sürüm 0.1.0
Bulgu: 0  ·  KRİTİK 0  ·  UYARI 0  ·  BİLGİ 0
------------------------------------------------------------------------
Bugün aksiyon gerektiren bir şey yok. 🎉
```

Aynı sonuç, canlı uç nokta `200` ile `{"content": []}` döndürdüğünde alınır; `--source fixture`
ile boş bir veri klasörü de birebir aynı metni üretir.

**Neden.** İki durum aynı görünür: (a) gerçekten aksiyon gerektiren kayıt yok, (b) satıcının
verisi var ama sorgu penceresine girmiyor. Kural motoru yalnızca `since`/bugünden sonrasına ve
okunabilen kayıtlara bakar.

**Çözüm.** Bu bir hata değildir, çıkış kodu 0'dır. "Beklediğim veri nerede?" sorusunda `check`
çıktısındaki `kayıtlar` satırına bakın (`siparis 0, iade 0, urun 0, yorum 0` → veri gelmiyor);
sayılar sıfırdan büyükse pencere/`--now` değerini kontrol edin. Ayırt etmek için JSON özeti
kullanışlıdır: `demo --json` içinde `"count": 0` ve `"findings": []` alanları açıkça görünür.

## 6) Uç nokta yok: `not:` satırı

**Belirti.** Özetin sonunda, bulgulardan bağımsız bir uyarı bloğu çıkar:

```console
$ HEPSIBURADA_MERCHANT_ID=123 HEPSIBURADA_API_KEY=dummy \
    HEPSIBURADA_ORDERS_BASE_URL=http://127.0.0.1:8790 \
    HEPSIBURADA_LISTING_BASE_URL=http://127.0.0.1:8790 trendyol-mcp --source hepsiburada demo
GÜNLÜK SATICI ÖZETİ — 06.10.2026 16:08
Kaynak: hepsiburada  ·  Kural motoru: sürüm 0.1.0
Bulgu: 0  ·  KRİTİK 0  ·  UYARI 0  ·  BİLGİ 0
------------------------------------------------------------------------
Bugün aksiyon gerektiren bir şey yok. 🎉
------------------------------------------------------------------------
not: hepsiburada satıcı API'si ürün yorumlarını okumaya izin vermiyor; cevapsız olumsuz yorum kuralı bu kaynakta atlandı.
not: Metrikler yalnızca sipariş, iade ve listeleme verisinden üretildi.
```

**Neden.** Her pazaryeri aynı veriyi sunmaz; Hepsiburada satıcı API'sinde ürün yorumu okuma uç
noktası yoktur (`supports_reviews = False`, bkz. `docs/rules.md` yetenek matrisi).

**Çözüm.** Beklenen davranıştır, düzeltilecek bir şey yoktur: `check` çıktısı da
`yorum okuma : bu pazaryerinde uç nokta yok` der. Önemli olan, eksik verinin **sessizce**
yutulmaması ve raporun hangi kuralın atlandığını `not:` ile söylemesidir.

## 7) Örnek veri bozuk veya eksik

**Belirti** (üç ayrı durum, üç ayrı mesaj — hepsi kod 1 ile biter):

```console
$ TRENDYOL_MCP_FIXTURES=C:/yok_boyle_klasor trendyol-mcp demo --source fixture
hata: Fixture klasörü eksik veya geçersiz: C:\yok_boyle_klasor (meta.json bulunamadı)

$ trendyol-mcp demo --source fixture --fixtures C:/tmp/meta_var_dosyalar_yok
hata: Fixture dosyası yok: orders.json

$ trendyol-mcp demo --source fixture --fixtures C:/tmp/bozuk_sema
hata: orders.json şemaya uymuyor: 7 hata
```

**Neden.** `--source fixture` beklenen dosyaları (`meta.json`, `orders.json`, `returns.json`,
`products.json`, `reviews.json`) bulamıyor ya da içerik normalize modellere uymuyor.

**Çözüm.** Doğru klasörü `--fixtures` ile verin veya `TRENDYOL_MCP_FIXTURES` değişkenini
tanımlayın. Şema hatasında eksik/yanlış alanları düzeltin; şema sözleşmesi için
`tests/factories.py` ve `examples/data/` referanstır. Şema hatası **tahmin edilerek yutulmaz** —
sessizce boş liste döndürmek yanlış bir "her şey yolunda" raporu üretirdi.

## Çıkış kodları

| Kod | Anlam |
|-----|-------|
| `0` | Başarılı. Bulgu olmaması da başarıdır (bkz. [5](#5-boş-veri-bulgu-yok)). |
| `1` | `AdapterError`: kimlik bilgisi, HTTP veya örnek veri kaynaklı hata. Mesaj `hata: …` olarak **stderr**'e yazılır. |
| `2` | Kullanım hatası: alt komut yok veya argüman geçersiz. |

`hata:` satırının stderr'e gitmesi bilinçlidir: `demo --json` çıktısını bir boruya verip
hatayı ayrı yakalayabilirsiniz.

```console
$ trendyol-mcp --source yanlis demo
trendyol-mcp: error: argument --source: invalid choice: 'yanlis' (choose from auto, fixture, trendyol, hepsiburada)
$ echo $?
2
```

## Ek: HTTP senaryolarını yerelde yeniden üretme

401/403/429 ve boş yanıt davranışını gerçek bir satıcı hesabı olmadan doğrulamak için, tüm
isteklere sabit bir durum kodu döndüren küçük bir sahte sunucu yeterlidir. Yaptığım şey buydu:

1. Tek dosyalık bir `http.server` yazın; `GET` için `STUB_STATUS` kodunu ve `STUB_BODY` gövdesini
   döndürsün (gerekirse `STUB_PORT` ile port seçin).
2. Sahte sunucuyu başlatın, ardından temel adresi ona çevirerek CLI'yi çalıştırın:

   ```bash
   STUB_STATUS=429 STUB_PORT=8789 python stub.py &          # yerel sahte sunucu
   TRENDYOL_SUPPLIER_ID=123 TRENDYOL_API_KEY=dummy TRENDYOL_API_SECRET=dummy \
     TRENDYOL_BASE_URL=http://127.0.0.1:8789 uv run trendyol-mcp --source trendyol check
   ```

Bu senaryoları ağ olmadan, deterministik biçimde çalıştırmak isterseniz asıl güvence testlerdedir:
`uv run pytest tests/test_trendyol_adapter.py tests/test_hepsiburada_adapter.py` — `respx`
taklitleri aynı 401/429/şema yollarını doğrular.
