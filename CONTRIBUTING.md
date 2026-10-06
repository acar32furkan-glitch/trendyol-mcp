# Katkı Rehberi

Teşekkürler! Bu proje **salt okunur** kalmayı bir tasarım ilkesi olarak benimser; katkıların
tamamı bu ilkeye uymalıdır.

## Hızlı kurulum

```bash
git clone https://github.com/acar32furkan-glitch/trendyol-mcp
cd trendyol-mcp
uv sync --all-extras --dev
uv run trendyol-mcp --source fixture demo   # kimlik bilgisi gerekmez
```

## Kalite kapısı (PR öncesi hepsi yeşil olmalı)

```bash
uv run ruff check .          # lint
uv run ruff format --check . # biçim
uv run mypy                  # katı tip denetimi
uv run pytest                # testler (+ kapsam raporu)
```

`pre-commit install` ile aynı kontrolleri commit öncesine bağlayabilirsiniz.

## Tasarla ilkeler

1. **Salt okunur.** Hiçbir adaptör veya araç satıcı hesabında değişiklik yapmaz. Yazma
   gerektiren bir özellik istiyorsanız önce `docs/adr/` altında bir karar kaydı açın.
2. **Kural ≠ rapor.** Hesaplama `src/trendyol_mcp/domain/` içinde saf fonksiyon olur; metin
   üretimi `render.py` içinde kalır. Böylece aynı bulgu hem CLI'da hem MCP'de aynı görünür.
3. **Zaman enjekte edilir.** Kural fonksiyonları `now` parametresi alır; testler sabit bir
   zamana göre çalıştığı için sonuçlar tekrarlanabilir olur.
4. **Yeni pazaryeri = yeni dosya.** `adapters/hepsiburada.py` ekleyip `adapters/__init__.py`
   içinde dışa açmanız yeterli; kural motoru değişmez.
5. **Yeni kural = yeni eşik.** Eşikler `Thresholds` üzerinden geçer ve `docs/rules.md`'de
   belgelenir.

## Kullanıcıya dönük metin

Bulgular Türkçe ve **eylem odaklı** yazılır: `title_tr` ne olduğunu, `detail_tr` hangi kaydı
etkilediğini, `action_tr` bugün ne yapılacağını söyler. Örnek mesajları `docs/rules.md`'de
bulabilirsiniz; yeni kural eklerken aynı tonu koruyun.

## Commit ve PR

- Conventional Commits: `feat(kural):`, `fix(mcp):`, `docs:`, `test:`, `chore:`.
- Her PR tek bir konuyu ele alır; açıklamada "ne / neden / nasıl test edildi" bulunur.
- `CHANGELOG.md` aynı PR içinde güncellenir (sürüm notu otomatik değil, bilinçli yazılır).
- PR şablonundaki kontrol listesini doldurun.

## Veri ve gizlilik

- **Gerçek kimlik bilgisi, API anahtarı, müşteri adı, sipariş numarası eklemeyin.** Örnek veri
  anonimleştirilmiş ve `examples/data` altında tutulur.
- Yeni örnek veri eklerken `meta.json` içindeki `reference_time` ile tutarlı zaman damgaları kullanın
  (demo ve testler bu çapaya göre çalışır).

## Lisans

Katkılarınız MIT lisansı altında yayınlanır.
