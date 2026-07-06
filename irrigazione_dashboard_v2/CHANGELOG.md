## 10.5.17
- Gli aggregati e-Dry (`zones_info`, `programs_info`, `meteo_info` e switch programmi) vengono risolti prima tramite `bind_config_entry_id`, cosi l'add-on funziona anche con entity_id prefissati da Home Assistant.
- Aggiunta diagnostica nel log `/api/irrigazione/state` e nella pagina entita per indicare se gli aggregati arrivano da bind, configurazione esplicita o risultano mancanti.

## 10.5.16
- Mostrati nella dashboard e-Dry altri dati stazione reale e-SunMind: stazione, raffica vento, pioggia oggi, radiazione, UV, VPD ed ET0.
- Esteso `/api/device_weather` con i principali parametri meteo professionali quando disponibili.

## 10.5.15
- Spostato il campo `Minuti` accanto ai pulsanti `Tutte` e `Nessuna` nel riquadro `Irriga ora`.

## 10.5.14
- Riorganizzato `Irriga ora` per allargare la lista zone invece di allungarla verticalmente.
- Ridotto lo spazio vuoto nel pannello manuale e resa la disposizione piu bilanciata su desktop e mobile.

## 10.5.13
- Migliorato il riquadro `Irriga ora`: lista zone piu grande, responsive e con scrollbar in stile dashboard.
- Stilizzati gli slider durata zona per evitare controlli browser grezzi.
- Rimosso il carattere `?` visibile in alto a sinistra prima del caricamento pagina.

## 10.5.12
- Ridotto il carico CPU del dashboard con refresh adattivo: 5 secondi a riposo, 1,5 secondi solo con irrigazione attiva e 15 secondi quando la pagina non e visibile.
- Ridotta la frequenza dei log backend `/api/irrigazione/state`.

## 10.5.11
- Aggiunto pulsante `Esporta storico` nel popup Eventi per scaricare il registro eventi in CSV.

## 10.5.10
- Rinominata la pagina manuale in `Guida utente e-Dry`.

## 10.5.9
- Aggiunta pagina `Manuale` apribile dal menu hamburger.
- Le tarature meteo richiedono la password a ogni apertura e il popup si apre solo dopo validazione admin.

## 10.5.8
- Aggiunto `Test impianto`: esegue tutte le zone in sequenza per 30 secondi ciascuna.
- La sequenza manuale ora supporta anche durate sotto 1 minuto per funzioni diagnostiche.

## 10.5.7
- Aggiunto pannello `Programma in corso` con programma, zona corrente, residuo, prossima zona e barra avanzamento.
- Aggiunti comandi `Salta zona` e `Stop programma` nella sezione Programmi.

## 10.5.6
- Aggiunto pannello `Sequenza manuale` in stile centralina professionale: zona in corso, tempo residuo, prossima zona e barra avanzamento.
- Aggiunto pulsante `Salta zona` per passare alla zona successiva senza fermare tutta la sequenza.

## 10.5.5
- Corretto `Irriga ora`: la durata scelta viene passata a `e_dry.start_zone_for`.
- Con piu zone selezionate l'add-on esegue una sequenza reale: ogni zona resta attiva per i minuti scelti prima di passare alla successiva.
- `STOP TUTTO` cancella anche la sequenza rapida in corso.

## 10.5.4
- Aggiunto pulsante `STOP TUTTO` direttamente nel riquadro `Irriga ora`, comodo soprattutto su smartphone.
- Unificata la logica di stop totale tra menu e riquadro rapido.

## 10.5.3
- Corretto layout smartphone: Zone e Programmi ora vanno in una sola colonna e `Irriga ora` non viene piu schiacciato.
- Migliorato il wrapping dei testi lunghi nelle card programma su schermi stretti.

## 10.5.2
- `Irriga ora` ora permette di selezionare una o piu zone tramite checkbox.
- I pulsanti 5/10/15 minuti impostano solo la durata: l'irrigazione parte soltanto premendo `Irriga ora`.

## 10.5.1
- Aggiunto riquadro `Irriga ora` sopra le zone con scelta zona, durata personalizzata e scorciatoie 5/10/15 minuti.
- Mantenuti invariati i pulsanti `Avvia` e `Stop` dentro ogni card zona.

## 10.5.0
- Rese piu leggibili le card programma con frasi naturali: partenza, zone irrigate e pausa tra zone.
- Aggiunto badge stato programma `Attivo` / `Disattivato`.

## 10.4.2
- Aggiunto pulsante `Elimina` sui programmi con conferma prima della cancellazione.

## 10.4.1
- Reso piu chiaro il ragionamento SmartCalc per utenti finali.
- `Score meteo` viene mostrato come `Condizioni per irrigare` con valori Buone/Discrete/Sfavorevoli.
- `ET0` viene mostrato come `Quanto asciuga il terreno` con valori Basso/Medio/Alto.

## 10.4.0
- Aggiunta creazione programmi dalla dashboard add-on tramite pulsante `Nuovo programma`.
- Aggiunto endpoint `POST /api/programs/create` collegato al servizio component `e_dry.create_program`.
- Aggiunto fallback automatico a `e_dry.update_program` con `program_id: 0` se il nuovo servizio non e ancora disponibile.
- Mantenuta la fix del pulsante `Modifica` programmi, ora stabile durante i refresh periodici.

## 10.3.2
- Reso immediato e stabile il pulsante `Modifica` dei programmi: apertura su pointerdown e refresh periodico sospeso mentre il pannello e aperto.

## 10.3.1
- Corretto il layout dei badge nelle card zona: ora usano sempre due colonne e non vengono piu tagliati nelle card strette.

## 10.3.0
- Ripulite le card zona: preset e durate sono ora badge/metriche compatti invece di testo in linea.
- Migliorata la leggibilita della parte bassa delle card e il layout responsive su schermi stretti.

## 10.2.2
- Spostata fisicamente la decorazione sprinkler sotto l'area delle scritte delle zone.
- Lo sprinkler resta nascosto quando la zona e OFF e appare solo durante l'irrigazione.

## 10.2.1
- Portate le scritte finali delle card zona sopra la decorazione sprinkler, migliorandone la leggibilita.

## 10.2.0
- Aggiunta panoramica `Prossima irrigazione`, calcolata dai programmi abilitati per i successivi sette giorni.
- Mostrati programma e zone coinvolte nella prossima partenza.
- Aggiunto riepilogo `Decisione SmartCalc` con stato meteo e motivazione prodotta dal component.

## 10.1.1
- Corretto lo sfondo del tema prototipo: ora copre l'intera viewport, resta centrato e non viene ripetuto a quadrati.

## 10.1.0
- Prima UI prototipo in stile centralina professionale, sviluppata su branch reversibile dedicato.
- Aggiunta panoramica operativa con stato impianto, zona attiva, numero zone, programmi e fattore SmartCalc.
- Aggiornata gerarchia visiva con palette blu/verde acqua e layout responsive, senza modificare API o logica di controllo.

## 10.0.10
- Aggiunta la route HTTP dedicata al logo EKONEX, che ora viene caricato correttamente nella dashboard.

## 10.0.9
- Aggiunto il logo EKONEX traslucido al centro dell'intestazione della card meteo, con dimensionamento responsive.

## 10.0.8
- Ripristinata l'icona hamburger del menu usando tre barre HTML/CSS, evitando sostituzioni dovute alla codifica dei caratteri.

## 10.0.7
- Corretto popup admin `Tarature meteo`: ora ha scroll interno e blocca lo scroll della pagina sottostante.
- Migliorata usabilita su viewport piccoli per raggiungere pulsanti e campi in fondo al popup.

## 10.0.6
- Aggiunta sezione admin `Preset zone` dentro `Tarature meteo`.
- Aggiunta API protetta `GET/POST /api/irrigazione/zone_profiles` per leggere preset, assegnarli alle zone e salvare preset custom.
- Le assegnazioni e i preset custom vengono salvati dal component e-Dry tramite `e_dry.update_zone` e `e_dry.update_zone_profiles`, quindi restano persistenti dopo restart.
- Le card zona mostrano il preset attivo e il moltiplicatore SmartCalc applicato.

## 10.0.5
- Protetta la sezione `Tarature meteo` con password admin configurabile tramite `admin_settings_password`.
- Rimossa dalla dashboard la modifica diretta delle entita fallback per evitare errori lato cliente.
- Le entita fallback restano visibili solo come diagnostica; soglie e SmartCalc restano modificabili da admin.

## 10.0.4
- Aggiunto popup `Tarature meteo` nella dashboard per vedere e modificare SmartCalc, endpoint e-SunMind, soglie pioggia/vento/gelo e sensori fallback.
- Aggiunta API add-on `GET/POST /api/meteo/weather_settings` collegata al servizio component `e_dry.update_weather_settings`.
- Allineate versioni runtime add-on a `10.0.4`.

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








































