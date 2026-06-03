# NOTES_FOR_AGENT

<agents_md>
Ogni volta che fai modifiche a questo addon:
1) incrementa SEMPRE la versione (bump) dell’addon
2) aggiorna SEMPRE questo file con un log sintetico delle modifiche effettuate (file toccati + cosa è cambiato)
</agents_md>

## Log modifiche (append-only)
- 2026-01-14: bump versione a `2.0.3`, rinominato addon in `e-Dry Irrigazione`, aggiornato logo dashboard a `e-dry2.png`, aggiunti `icon.png`/`logo.png` (HA tile).
- 2026-06-03: bump versione a `10.0.1`; allineati `config.yaml`, `web/server.py`, `web/entities_server.py`, badge UI e riferimenti installativi/diagnostici.
- 2026-06-03: bump versione a `10.0.2`; meteo dashboard migrato a e-SunMind (`e_sunmind_api_url`), disattivato fallback OpenWeather e ripuliti placeholder UI corrotti.
- 2026-06-03: bump versione a `10.0.3`; `config.yaml`, `web/server.py` e `web/entities_server.py` ora usano `GET /api/weather/irrigation` di e-SunMind, campi meteo irrigazione normalizzati e conversione automatica del vecchio URL `/api/data`.
