# ADR-0003 — Yalnızca stdio taşıması

- **Durum:** Kabul edildi
- **Tarih:** 2026-10-19
- **Karar verenler:** proje sürdürücüsü

## Bağlam

MCP belirtimi iki standart taşıma tanımlar: stdio ve Streamable HTTP. Streamable HTTP,
2024-11-05 sürümündeki HTTP+SSE taşımasının yerini almıştır
([belirtim, 2025-06-18 · Transports](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)).
Belirtim stdio'yu "istemci sunucuyu alt süreç olarak başlatır" diye tarif eder; Streamable HTTP'de ise
"sunucu bağımsız bir süreç olarak çalışır ve birden çok istemci bağlantısına hizmet edebilir".

Bu projedeki sunucu **tek bir satıcının kendi hesabını** okur. Kimlik bilgisi süreç ortamından gelir
ve süreç başına tek kimlik kümesi vardır:

```python
# src/trendyol_mcp/config.py:28
def from_env(cls, env: dict[str, str] | None = None) -> TrendyolCredentials | None:
```

`cmd_serve` tek bir `provider` kurup `run_stdio`'ya verir (`src/trendyol_mcp/cli.py:187-192`), o da
sunucuyu yalnızca stdio ile başlatır (`src/trendyol_mcp/server.py:67`). Depoda oturum, kiracı ya da
istemci kimlik doğrulama katmanı yoktur: `grep -rniE "auth|tenant|session|token" src` 8 satır döndürür
ve hepsi ya pazaryeri HTTP Basic başlığını üreten satırlardır (`adapters/trendyol.py:79`,
`adapters/hepsiburada.py:128`) ya da "authored"/"authentication" kelimesi geçen docstring'lerdir.

Kısıt teknik bir eksiklik değil: kurulu SDK üç taşımayı da sunuyor, CLI ise hiçbirini seçtirmiyor.

```text
$ uv run trendyol-mcp serve --help
usage: trendyol-mcp serve [-h] [--source {auto,fixture,trendyol,hepsiburada}]
                          [--fixtures FIXTURES] [--now NOW] [--json]
```

```text
# inspect.signature(MCPServer.run) — kurulu mcp paketi
(self, transport: "Literal['stdio', 'sse', 'streamable-http']" = 'stdio', **kwargs: 'Any') -> 'None'
run_sse_async(self, *, host: str = '127.0.0.1', port: int = 8000, sse_path: str = '/sse', ...)
run_streamable_http_async(self, *, host: str = '127.0.0.1', port: int = 8000,
                          streamable_http_path: str = '/mcp', ...)
```

## Karar

1. Sunucu **yalnızca stdio** üzerinden konuşur. `serve` komutu taşıma, host veya port parametresi almaz.
2. SDK'daki `sse` / `streamable-http` taşımaları bilinçli olarak açılmaz. Açmak yeni bir karar kaydı
   gerektirir; bir `--transport` bayrağıyla yapılmaz.
3. Ağ üzerinden paylaşım kapsam dışıdır. Ekip için planlanan çıkış ters yöndedir: raporun e-posta /
   webhook ile **dışarı itilmesi** (yol haritası v0.2.0 `report`), içeri doğru bir API değil.

Gerekçe: HTTP taşıması kimlik bilgisini istemcinin sürecinden ayırıp kalıcı bir dinleyicinin belleğine
taşır. O porta erişebilen her istemci, satıcının tam okuma kapsamıyla çalışır. Bunu güvenli kılmak için
gereken katmanlar — TLS sonlandırma, istemci kimlik doğrulaması, satıcı başına kimlik bilgisi kasası,
istek başına yetki — bu depoda yoktur. Onlar olmadan HTTP açmak, "kimlik bilgisini koruyan bir katman
olmadan kimlik bilgisi barındırmak" olurdu.

## Sonuçlar

**Olumlu**
- Dinlenen soket yok: yetkilendirilecek bir yüzey, LAN'a açılacak bir port yok. Anahtar, istemcinin
  kendi başlattığı sürecin ortamında kalır ve süreç bitince birlikte biter.
- İstemci başına süreç: iki istemci iki ayrı kimlik kümesiyle çalışabilir; istemci kapanınca sunucu da
  kapanır, ortada sahipsiz bir dinleyici kalmaz.
- Değerlendirme yolu üretim yoluyla aynıdır: `git clone` → `demo` → istemci yapılandırması. Dağıtım
  adımı, sertifika, ters vekil yok. `tests/test_server_mcp.py` gerçek sunucuyu `stdio_client` ile
  başlatıp el sıkışma, araç listesi ve araç çağrısını doğrular — test edilen yol, kullanılan yoldur.

**Olumsuz**
- Ekip kullanımında her makine kendi ortam değişkenlerini taşır; merkezî tek kurulum yoktur
  (yol haritası v1.0.0'daki OS keyring desteği de makine başına kalır).
- Tarayıcı tabanlı / barındırılan, yalnızca HTTP konuşan MCP istemcileri bu sunucuyu doğrudan
  bağlayamaz. README'deki bağlantı bölümü, istemcinin `command` ile alt süreç başlattığı istemcileri
  tarif eder.
- Sunucu tarafında kalıcı oturum veya çok kiracılı durum sunulamaz; böyle bir sürüm önce kimlik
  doğrulama ve satıcı başına kasa işini gerektirir.

## Alternatifler

1. **Streamable HTTP + paylaşılan gizli anahtar:** tek ortak sır satıcı ayrımı sağlamaz; satıcı başına
   kasa ve istek başına yetki olmadan çok kiracılı hâle gelmez. Tek satıcılı kurulumda ise stdio'nun
   verdiği izolasyonu kaybettirir, karşılığında bir şey kazandırmaz.
2. **HTTP+SSE (eski taşıma):** belirtimde Streamable HTTP'nin yerini aldığı taşıma; aynı kimlik bilgisi
   sorunlarını taşır ve yeni bir proje için geriye dönük seçim olurdu.
3. **Yalnızca `127.0.0.1`'e bağlı yerel HTTP:** maruziyeti azaltır ama kimlik bilgisi vesayetini
   kaldırmaz; istemci süreci zaten kendisi başlattığı için stdio'ya göre ölçülebilir bir kazanç yok.

## Doğrulama

Bu kayıttaki iddialar 2026-10-19'da depo kökünde şu komutlarla ölçüldü:

- `uv run trendyol-mcp serve --help` → yukarıdaki çıktı; `--transport`, `--host`, `--port` yok.
- `grep -rn 'run("stdio")' src` → tek eşleşme: `src/trendyol_mcp/server.py:67`.
- `grep -rniE "auth|tenant|session|token" src` → 8 satır: pazaryeri Basic auth başlıkları ve
  "authored"/"authentication" geçen docstring'ler. İstemci kimlik doğrulaması, oturum veya kiracı kodu
  yok.
- `inspect.signature(MCPServer.run)` (kurulu `mcp` paketi) → `Literal['stdio', 'sse',
  'streamable-http']`; `run_sse_async` ve `run_streamable_http_async` mevcut, yani HTTP yolu bir
  bağımlılık eksiği değil.
- Belirtim tarafı: standart taşımalar stdio ve Streamable HTTP; HTTP+SSE 2024-11-05 sürümünde kaldı
  (yukarıdaki bağlantı).
