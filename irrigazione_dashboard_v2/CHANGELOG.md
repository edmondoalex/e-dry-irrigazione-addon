## 10.0.3
- `/api/device_weather` ora consuma il contratto normalizzato e-SunMind `GET /api/weather/irrigation`.
- Aggiornati default `e_sunmind_api_url` e parser meteo per usare campi irrigazione gia normalizzati.
- Se nelle opzioni add-on resta salvato il vecchio `/api/data`, viene convertito automaticamente a `/api/weather/irrigation`.
- Allineati dashboard principale, server debug entita e badge versione a `10.0.3`.

## 10.0.2
- Meteo dashboard migrato a e-SunMind tramite opzione `e_sunmind_api_url`.
- `/api/device_weather` ora legge `/api/data` di e-SunMind e usa solo sensori HA `sensor.e_sunmind_weather_*` come fallback.
- Anche il server debug entita usa e-SunMind per `/api/device_weather`.
- Rimossi dalla configurazione add-on i riferimenti legacy `owm_device_id` e `weather_entity`.
- Ripuliti placeholder meteo corrotti nella UI.

## 10.0.1
- Bump versione add-on a `10.0.1`.
- Allineate versioni tra manifest add-on, dashboard e server debug entita.
- Aggiornati riferimenti installativi alla cartella `irrigazione_dashboard_v2`.
- Aggiunto endpoint stats `/addons/irrigazione_dashboard_v2/stats`, mantenendo compatibilita col path legacy.

## 2.0.2
- Aggiunto pulsante "Eventi" nella card Meteo (popup da sensor.e_dry_event_log).

## 2.0.1
- Uniformato stile delle 3 card (bordi/sfondo).
- Aggiunto overlay "erbetta" allo sfondo (disattivabile impostando --grass-opacity:0).
- Backup automatico in web/_pgbackup/v2.0.1-style-*.
## 2.0.0

- Bump versione major a 2.0.0 + backup file principali.

## 1.40.312

- Card Programmi: rimossi i pulsanti `Start` e `Stop` (non utili).

## 1.40.311

- Card Meteo: lo slider "Regolazione Stagionale" ora usa il riempimento verde (stile slider zona durata).

## 1.40.310

- Card Meteo: la barra diventa slider bidirezionale per `number.regolazione_stagionale` (manual adjustment %).

## 1.40.309

- Card Programmi: rimosso lo slider del progresso; la barra sopra ora mostra lâ€™avanzamento (verde) + percentuale testuale.

## 1.40.308

- Slider durata: evita rollback visivo preferendo `configured_duration` (sensore aggregato) e persistenza robusta (`number.set_value` + `e_dry.update_zone`).

## 1.40.307

- Debug entitÃ  (porta `1978`): risoluzione entitÃ  per-zona tramite entity registry usando `unique_id_prefix` (piÃ¹ fallback), cosÃ¬ ruoli come `Ignora Meteo`/`Durata`/`Remaining`/`Progress` risultano popolati.

## 1.40.306

- Pagina debug entitÃ  (porta `1978`): sezione meteo/programmi aggregati + riferimenti (sensori meteo e switch fisici).
- Dashboard (porta `1977`): aggiunto pulsante `Entita` per aprire la pagina debug con `config_entry` precompilato.

## 1.40.305
- Card Zone: risoluzione sensori per-zona piÃ¹ robusta (usa entitÃ  del `config_entry` + fallback deterministico `zona_{id}` / `{id}_`), eliminando i `null` in `remaining_entity/percent_entity/duration_entity/ignore_meteo_entity`.
- `GET /api/irrigazione/state`: prova anche lâ€™Entity Registry (`/api/config/entity_registry/list`) per risolvere le entitÃ  legate al `config_entry` quando il template non restituisce risultati.
## 1.40.304
- Card Zone: stato ON/OFF solo da `zones_info.active` (rimosso fallback su `remaining` lato UI) per evitare riaccensioni dopo STOP.
- `GET /api/irrigazione/state`: per-zona usa i sensori reali legati al `config_entry` (durata/remaining/progresso/ignora meteo) e usa `zones_info` solo come lista + `active/ignore_weather` (niente discovery, niente calcoli).
## 1.40.303
- Pagina EntitÃ  (porta 1978): raggruppamento allineato ai sensori aggregati (`sensor.e_dry_zones_info`, `sensor.e_dry_programs_info`, `sensor.e_dry_meteo_info`) + sezione Aggregati e gruppi Programma.
- Pagina EntitÃ : auto-compila `bind_config_entry_id` da `/api/options` se non passato in querystring.
## 1.40.302
- Card Zone: fix stato sempre ON (non usa piÃ¹ il progresso % come fallback; percent calcolato solo quando la zona Ã¨ attiva).
## 1.40.301
- Card Zone: lista zone SOLO da `sensor.*_zones_info` (niente discovery) e parsing booleano robusto (`active`/`ignore_weather`) per evitare tutte le zone ON.
- Azioni Zone: start/stop via `e_dry.start_zone`/`e_dry.stop_zone` (solo `zone_id`).
- Slider/toggle: `duration_set` e `ignore_meteo` accettano `zone_id` e usano `e_dry.update_zone` (piÃ¹ stabile).
## 1.40.300
- Ripristinato `web/server.py` e `server.py` da backup pulito, eliminando errori di indentazione/sintassi e crash dellâ€™add-on.
- `GET /api/irrigazione/state`: usa i sensori aggregati `sensor.e_dry_zones_info`, `sensor.e_dry_programs_info`, `sensor.e_dry_meteo_info` come fonte dati primaria.
- `POST /api/programs/enabled`: toggle bidirezionale sullo switch reale `switch.programmi_abilitati` (niente piÃ¹ 400/404 se manca il bind).
- `POST /api/irrigazione/stop_all`: stop generale via `e_dry.stop_zone` sulle zone attive (fallback legacy).
- `POST /api/programs/update`: sanitizzazione nome programma e rimozione `time=disabled` per evitare duplicazioni â€œCentralina Irrigazione â€¦ scheduleâ€.
## 1.40.263
- Programmi abilitati: stato e entity via sensore aggregato; lettura dallo switch `switch.programmi_abilitati` (fallback).
- Versioni allineate a 1.40.263.

## 1.40.203
- Allineate versioni (config/index/server/README) alla 1.40.203.
- Logo e-dry servito dal backend senza 404 e mostrato nella card Meteo.
- UI Programmi: chip giorni/zone e pausa visibili; form modifica resta aperto finchÃ© non si salva/annulla; proxy e_dry.update_program.
- Progress zone: usa anche percent_raw come fallback.

## 1.4.143
- Ripristinato server.py pulito (niente caratteri BOM). Aggiunto endpoint /api/programs/update e dati programmi (giorni/zone/pause) letti da options per la UI.
- Sistema versioni allineato.

## 1.4.142
- Fix SyntaxError (chiusure script) e rendering Programmi inline; programma update via /api/programs/update.
- UI Programmi: chip giorni/zone, form modifica completo, start/stop, toggle abilitati, barra progresso.

## 1.4.141 (programmi UI)
- Card Programmi ridisegnata: toggle abilitati, mini-card per programma con giorni, zone, pausa, ora. Modifica inline via e_dry.update_program.
- Aggiunto endpoint /api/programs/update per proxy al servizio di integrazione.
- Progress zone: parsing percentuale migliorato.

## 1.4.141
- STOP TUTTO piÃ¹ robusto: tenta stop per ogni zona attiva e poi gli endpoint globali/legacy.
- Barra progresso zone: fallback calcolato da remaining/durata se percentuale mancante.
- Pulizia testi pulsanti Avvia/Stop (niente caratteri strani). Version bump allineato.

## 1.4.139
- Evitati errori JS se i controlli in header non esistono: guard su refresh/stop_all e toggle compatto/ricerca. Version bump allineato.

## 1.4.137
- Header Meteo: sostituiti icona/testo con logo e-dry, aggiunti controlli (durata, cerca, compatta, export, aggiorna, STOP) e stato online; testata principale lasciata vuota. Version bump allineato.

## 1.4.136
- Ripristinata chiusura script (SyntaxError risolto), fallback di testo puliti ('-') per meteo; zona attiva calcolata con fallback prima zona ON. Version bump allineato.

## 1.4.135
- Zona attiva spostata nella card Zone: mostra il nome della zona in irrigazione (fallback prima zona ON, altrimenti '-'). Version bump allineato.

## 1.4.133
- Header superiore svuotato; controlli (durata, ricerca, compatta, export, aggiorna, stop tutto) e stato spostati nell'header della card Meteo con logo. Icone Avvia/Stop semplificate (testo).








































