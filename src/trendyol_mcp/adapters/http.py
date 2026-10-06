"""Dayanıklı, salt okunur JSON isteği.

İki pazaryeri adaptörü de aynı politika ile çağrı yapar:

* yalnızca ``GET``,
* 429/5xx → üstel geri çekilme ile yeniden dene,
* 401 → "kimlik bilgisi reddedildi" mesajı (anahtar değeri asla loglanmaz),
* 4xx → anlaşılır hata, denemeyi tekrarlamadan dur.
"""

from __future__ import annotations

import time
from typing import Any, Final

import httpx

from trendyol_mcp.adapters.base import AdapterError

RETRY_STATUS_CODES: Final = frozenset({429, 500, 502, 503, 504})
USER_AGENT: Final = "trendyol-mcp/0.1.0 (+https://github.com/acar32furkan-glitch/trendyol-mcp)"


def request_json(
    client: httpx.Client,
    path: str,
    params: dict[str, Any],
    *,
    max_retries: int = 3,
    backoff_seconds: float = 0.5,
) -> dict[str, Any]:
    """Perform a read-only GET and return the decoded JSON object.

    Raises:
        AdapterError: on authentication failure, client error, or exhausted retries.
    """
    query = {key: value for key, value in params.items() if value is not None}
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            response = client.get(path, params=query)
        except httpx.HTTPError as exc:
            last_error = exc
        else:
            if response.status_code == 401:
                raise AdapterError(
                    "Kimlik bilgileri reddedildi (HTTP 401). Sağlayıcı panelinden üretilen "
                    "anahtar/şifre değerlerini kontrol edin."
                )
            if response.status_code in RETRY_STATUS_CODES:
                last_error = AdapterError(f"{path} geçici hata döndü: HTTP {response.status_code}")
            elif response.status_code >= 400:
                raise AdapterError(f"{path} isteği başarısız: HTTP {response.status_code}")
            else:
                try:
                    payload: object = response.json()
                except ValueError as exc:
                    raise AdapterError(f"{path} yanıtı JSON olarak çözülemedi") from exc
                if not isinstance(payload, dict):
                    raise AdapterError(f"{path} beklenmeyen yanıt tipi döndürdü")
                return payload

        if attempt + 1 < max_retries:
            time.sleep(backoff_seconds * (2**attempt))

    raise AdapterError(f"{path} isteği {max_retries} denemede başarısız oldu: {last_error}")
