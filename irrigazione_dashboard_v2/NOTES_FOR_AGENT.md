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
- 2026-06-03: bump versione a `10.0.4`; aggiunti popup dashboard e API `/api/meteo/weather_settings` per vedere/modificare tarature meteo e SmartCalc dal componente e-Dry.
- 2026-06-03: bump versione a `10.0.5`; protetta `Tarature meteo` con `admin_settings_password` e bloccata la modifica entita fallback dalla dashboard cliente.
- 2026-06-03: bump versione a `10.0.6`; aggiunta sezione admin `Preset zone`, endpoint `/api/irrigazione/zone_profiles`, assegnazione preset per zona e creazione preset custom persistenti nel component e-Dry.
- 2026-06-03: bump versione a `10.0.7`; corretto popup admin per usare scroll interno e impedire lo scroll della pagina sottostante.
- 2026-06-04: bump versione a `10.0.8`; ripristinata icona hamburger del menu con tre barre HTML/CSS indipendenti dalla codifica.
- 2026-06-04: bump versione a `10.0.9`; aggiunto logo EKONEX traslucido al centro dell'intestazione della card meteo.
- 2026-06-04: bump versione a `10.0.10`; aggiunta route HTTP dedicata al logo EKONEX.
- 2026-06-04: bump versione prototipo a `10.1.0`; aggiunta panoramica operativa e UI stile centralina professionale sul branch `codex/controller-ui-prototype`.
- 2026-06-04: bump versione prototipo a `10.1.1`; corretto sfondo full viewport senza ripetizione.
- 2026-06-04: bump versione prototipo a `10.2.0`; aggiunte prossima irrigazione e decisione SmartCalc nella panoramica.
- 2026-06-04: bump versione prototipo a `10.2.1`; corretto livello delle scritte zona rispetto alla decorazione sprinkler.
- 2026-06-04: bump versione prototipo a `10.2.2`; spostato sprinkler fuori dalle scritte e nascosto quando la zona e OFF.
