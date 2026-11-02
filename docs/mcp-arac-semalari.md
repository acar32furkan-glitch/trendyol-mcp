# MCP araç şemaları: `tools/list` bir ajana ne anlatır

Bu sunucuya bağlanan bir modelin araç seçerken ve argüman kurarken gördüğü sözleşme yalnızca
`inputSchema` değildir: tek seferlik `instructions`, araç açıklaması, parametre adları, tipleri,
varsayılanları, `annotations` ve `outputSchema` birlikte okunur. Bu belge o yüzeyin **ne taşıdığını
ve ne taşımadığını** gerçek `tools/list` yanıtı ve gerçek `tools/call` hatalarıyla gösterir.

Ölçüm ortamı: `trendyol-mcp 0.1.0` · MCP protokolü `2025-11-25` · `mcp` 2.3.0 · `pydantic` 2.13.5 ·
kaynak `fixture`. Şema üretimi bu iki pakete bağlıdır; sürüm değişince aşağıdaki bayt sayıları da değişir.

## 30 saniyelik cevap

- Sunucu **8 araç** açıyor; hepsi `readOnlyHint: true, destructiveHint: false` işaretli. Sıkıştırılmış
  `tools/list` yanıtı **4.033 bayt** — her oturumda istemcinin bağlama eklediği sabit maliyet.
- Şema yalnızca **ad + tip + varsayılan** taşıyor. 8 aracın 13 parametresinin **hiçbirinde**
  `description`, `minimum`, `maximum` ya da `enum` yok; `required` alanı hiç üretilmemiş.
- Pratik sonucu: model **hangi aracı** çağıracağını doğru seçer (açıklamalar Türkçe ve tek cümle),
  **hangi argümanı** vereceğini şemadan bilemez. Parametre adını yanlış hatırlarsa hata almaz —
  çağrı varsayılanlarla çalışır ve "başarılı" görünen sonuç döner.

## Ölçümü yeniden üret

```bash
uv run python scripts/mcp_tool_schemas.py            # parametre tablosu (bu belgedeki tablonun kaynağı)
uv run python scripts/mcp_tool_schemas.py --json     # ham tools/list yanıtı
uv run python scripts/probe_mcp_client.py            # el sıkışma + araç listesi + bir çağrı
```

`scripts/mcp_tool_schemas.py` sunucuyu gerçekten stdio üzerinden başlatıp yanıtı okur; tablolar elle
yazılmadı. Çıktının başı (kısaltılmış):

```
trendyol-mcp 0.1.0 · protokol 2025-11-25 · 8 araç · tools/list 4033 bayt (sıkıştırılmış)

list_orders
  şema anahtarları : properties, title, type · required=<yok> · additionalProperties=<yok>
  - status              string|null varsayılan=None açıklama=<yok>
  - since               string|null varsayılan=None açıklama=<yok>
  - limit               integer    varsayılan=50 açıklama=<yok>
  çıktı şeması     : alanlar=<yok> · additionalProperties=True

stock_alerts
  şema anahtarları : properties, title, type · required=<yok> · additionalProperties=<yok>
  - threshold           integer    varsayılan=5 açıklama=<yok>
  çıktı şeması     : alanlar=<yok> · additionalProperties=True
```

## Alan alan: şema ne işe yarar

| Alan | Bu sunucudaki değer | Ajan tarafındaki işlevi |
|------|---------------------|-------------------------|
| `name` | `stock_alerts`, `daily_digest`… | Modelin seçim kararı ve `tools/call` içindeki çağrı kimliği. |
| `description` | 8/8 dolu, Türkçe tek cümle | **En çok kullanılan sinyal.** "Bu soru hangi araca ait?" kararı buradan verilir. |
| `inputSchema.properties.X.type` | `integer`, `string\|null` | Argüman kurma ve sunucu tarafı doğrulama. `{"threshold": "bes"}` reddedilir, `3.7` de reddedilir. |
| `inputSchema.properties.X.default` | `5`, `48`, `30`, `null` | Parametre atlanırsa ne olacağı. Model `{}` çağırırsa `threshold=5` kullanılır. |
| `inputSchema.required` | **yok** | Hiçbir alan zorunlu değil: `{}` her araç için geçerli. `required` alanının hiç olmaması, istemcilerin eksik-argüman uyarısı üretmemesi demek. |
| `annotations.readOnlyHint` | `true` | İstemci onay istemini hafifletir; `destructiveHint: false` "geri alınamaz iş yapmaz" güvencesi. |
| `annotations.openWorldHint` | `true` | Sonucun dış veriye dayandığını söyler (canlı kaynakta ağa çıkar). |
| `outputSchema` | `{"type":"object","additionalProperties":true,"title":"…DictOutput"}` | Sonraki adımı planlamak için **kullanılamaz**: alan adı taşımıyor. |
| `instructions` (initialize) | 620 bayt, Türkçe | Araç listesinden önce gelen tek seferlik davranış talimatı: "önce `daily_digest`, bulgular `severity` ile". |

## Ölçülen beş boşluk

Aşağıdaki her satır gerçek bir `tools/call` denemesinin sonucu; çıktılar birebir alındı.

**1. Bilinmeyen parametre sessizce yutuluyor.** `stock_alerts` aracına `{"esik": 3}` (Türkçe ad)
gönderildiğinde `is_error=false` ve `threshold=5` ile **aynı** sonuç döndü (`count=3`). Şemada
`additionalProperties` yok — JSON Schema'da bu "ek alan serbest" demektir ve sunucu ek alanı yok sayar.
Yani modelin yanlış hatırladığı parametre adı, hata değil **sessiz varsayılan** üretir.

**2. Aralık denetimi yok.** Şema `integer` diyor, sınır demiyor; sunucu da denetlemiyor:

| Çağrı | `is_error` | Dönen |
|-------|-----------|-------|
| `stock_alerts {"threshold": -1}` | `false` | `count=0` (hiçbir ürün eşiğin altında değil) |
| `return_clusters {"days": 0}` | `false` | `count=0`, `window_days=0` |
| `unanswered_reviews {"hours": -5}` | `false` | `count=2` — negatif pencere **geleceğe** bakar, sonuç anlamsız |

**3. Enum değerleri şemada yok.** `status` yalnızca `anyOf[{string},{null}]`. Geçerli değerler
`models.py` içinde (`created, picking, invoiced, shipped, delivered, cancelled, returned`) ama model
bunu şemadan göremez. Ölçüm: `status="cancelled"` → `count=1`, `status="delivered"` → `count=3`
(İngilizce değerler çalışıyor); `status="iptal"` → `is_error=true`, metin **yalnızca**
`Error executing tool list_orders` — geçerli değerleri söylemiyor, sunucu stderr'ine tam Python izi
düşüyor. Aynısı tarih için: `since="01.10.2026"` → aynı jenerik hata (beklenen `YYYY-MM-DD`).

**4. Tip doğrulaması pydantic'ten geliyor, şemadan değil — ve tutarsız.** `{"threshold": "bes"}` →
`Input should be a valid integer, unable to parse string as an integer` (iyi hata). Ama
`{"threshold": true}` → `is_error=false`, `count=1`: JSON `true` sessizce `1` sayılıyor. `{"threshold": 3.7}`
ise `got a number with a fractional part` ile reddediliyor. Yani `integer` alanı üç farklı
davranış gösteriyor; şemayı okuyan model bunu öngöremez.

**5. `outputSchema` boş, ama `structuredContent` dolu.** `stock_alerts` yanıtı
`structuredContent` içinde `source, count, counts, findings, threshold` taşıyor; şemada bu alanların
hiçbiri yok (`alanlar=<yok>`). Model çıktı yapısını ancak **çağrıdan sonra** öğrenir; "önce listele,
sonra daralt" gibi iki adımlı bir planı `tools/list` bilgisinden kuramaz.

## Bunun ajan tarafında pratik karşılığı

- **`{}` ile başla, sonra daralt.** Varsayılanlar satıcı için makul seçilmiş: `threshold=5`,
  `sla_hours=48`, `days=30`, `min_count=3`, `hours=24`.
- **Parametre adını tahmin etme.** Tek doğru kaynak `scripts/mcp_tool_schemas.py` çıktısı. Sonuç
  beklenmedik biçimde "temiz" görünüyorsa (0 bulgu) önce parametre adını denetle — 1. boşluk yüzünden
  yanlış ad hata üretmez.
- **`status` İngilizce enum değeriyle, `since` `YYYY-MM-DD` ile verilir.** Jenerik hata mesajı ipucu
  vermez; geçerli listeyi `models.py` / `trendyol-mcp tools` üzerinden al.
- **Negatif `days` / `hours` verme.** Kural motoru pencereyi geleceğe kaydırır, sonuç sessizce anlamsızlaşır.
- **`return_cluster_min` (daily_digest) ile `min_count` (return_clusters) aynı kuralın iki yüzeyidir.**
  Yanlış olanı yazmak hata vermez; doğru araçta doğru adı kullan.

## Düzeltmenin maliyeti (ayrı madde)

Üç boşluk tipler üzerinden deklarasyonla kapanabilir: `Annotated[int, Field(ge=0, description="…")]`
ile aralık + açıklama, `status: Literal["created", …] | None` ile enum. Dördüncüsü (bilinmeyen alan)
şema üretiminde `additionalProperties: false` gerektirir; `mcp` 2.3.0'ın imzadan şema üretirken bunu
destekleyip desteklemediği **ölçülmedi**, bu yüzden bu belge bir söz vermiyor. Bu değişiklikler
`tools/list` bayt sayısını ve dolayısıyla her oturumun bağlam maliyetini artırır: kazanç (doğru
argüman) ile maliyet (bayt) bu yüzden birlikte ölçülmelidir.

## Sınırlılıklar

- Bütün ölçümler `--source fixture` ile yapıldı; canlı Trendyol/Hepsiburada kaynağında şema **aynı**
  (şema adaptörden bağımsız, `ToolProvider` imzalarından üretiliyor) ama dönen `count` değerleri farklı olur.
- `inputSchema` üretimi `mcp` 2.3.0 + `pydantic` 2.13.5'e bağlı; sürüm yükseltmesi alan ekleyip
  kaldırabilir. `scripts/mcp_tool_schemas.py` bu yüzden depoda: yeni sürümde çıktı farkını gözle görürsün.
- Bu belge bir *gözlem* kaydıdır; şemayı değiştirmez. Değişiklik yapılırsa buradaki tablolar ve bayt
  sayısı aynı komutla yenilenmelidir.
