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
- 2026-06-05: bump versione prototipo a `10.3.0`; ripulite card zona con badge preset e metriche durata compatte.
- 2026-06-05: bump versione prototipo a `10.3.1`; corretto layout badge zona a due colonne per evitare tagli nelle card strette.
- 2026-06-05: bump versione prototipo a `10.3.2`; reso stabile il pulsante Modifica programmi sospendendo il refresh durante l'editing.
- 2026-06-05: bump versione prototipo a `10.4.0`; aggiunta creazione programmi da add-on tramite `e_dry.create_program`.
- 2026-06-05: bump versione prototipo a `10.4.1`; tradotto il ragionamento SmartCalc in frasi semplici per utenti finali.
- 2026-06-05: bump versione prototipo a `10.4.2`; aggiunta eliminazione programmi da dashboard con conferma.
- 2026-06-05: bump versione prototipo a `10.5.0`; rese piu leggibili le card programma con frasi naturali e badge stato.
- 2026-06-05: bump versione prototipo a `10.5.1`; aggiunto riquadro `Irriga ora` sopra le zone senza rimuovere i pulsanti `Avvia` nelle card.
- 2026-06-05: bump versione prototipo a `10.5.2`; `Irriga ora` supporta selezione multipla zone e i pulsanti durata non avviano piu automaticamente.
- 2026-06-05: bump versione prototipo a `10.5.3`; corretto layout mobile a colonna singola per Zone/Programmi e wrapping testi lunghi.
- 2026-06-05: bump versione prototipo a `10.5.4`; aggiunto `STOP TUTTO` nel riquadro `Irriga ora` e riusata logica stop totale comune.
- 2026-06-05: bump versione prototipo a `10.5.5`; corretto `Irriga ora` per usare `start_zone_for` e sequenza server temporizzata multi-zona.
- 2026-06-05: bump versione prototipo a `10.5.6`; aggiunto pannello sequenza manuale con zona corrente, residuo, prossima zona e comando `Salta zona`.
- 2026-06-05: bump versione prototipo a `10.5.7`; aggiunto pannello programma in corso con zona corrente/prossima/residuo e comandi `Salta zona`/`Stop programma`.
- 2026-06-05: bump versione prototipo a `10.5.8`; aggiunto `Test impianto` con sequenza di tutte le zone per 30 secondi ciascuna.
- 2026-06-05: bump versione prototipo a `10.5.9`; aggiunto manuale utente da hamburger e richiesta password admin a ogni apertura tarature meteo.
- 2026-06-05: bump versione prototipo a `10.5.10`; rinominato manuale in `Guida utente e-Dry`.
- 2026-06-05: bump versione prototipo a `10.5.11`; aggiunto export storico eventi CSV dal popup Eventi.
- 2026-06-05: bump versione prototipo a `10.5.12`; ridotto polling dashboard e throttling log stato per abbassare uso CPU.
- 2026-06-05: bump versione prototipo a `10.5.13`; migliorato layout `Irriga ora`, scrollbar/slider coerenti e rimosso carattere `?` iniziale.
- 2026-06-05: bump versione prototipo a `10.5.14`; lista zone `Irriga ora` allargata su griglia full width e altezza ridotta.
- 2026-06-05: bump versione prototipo a `10.5.15`; campo `Minuti` spostato nella riga strumenti accanto a `Tutte`/`Nessuna`.
- 2026-06-05: bump versione prototipo a `10.5.16`; dashboard mostra piu dati stazione reale e-SunMind e `/api/device_weather` espone nuovi parametri.
- 2026-07-06: bump versione a `10.5.17`; `web/server.py` e `web/entities_server.py` risolvono gli aggregati e-Dry tramite `bind_config_entry_id`/registry prima dei nomi fissi, con diagnostica sorgente nel log e JSON.
- 2026-07-06: bump versione a `10.5.18`; aggiunta risoluzione device registry per bind copiati dalla pagina dispositivo HA e log del bind effettivo in `/api/irrigazione/state`.
- 2026-07-06: bump versione a `10.5.19`; aggiunto fallback su `/api/states` per trovare gli aggregati e-Dry da nome/attributi quando registry e bind non bastano.
- 2026-07-06: bump versione a `10.5.20`; default backend e pagina entita allineati agli entity_id automatici `sensor.centralina_irrigazione_e_dry_*_info`.
- 2026-07-06: bump versione a `10.5.21`; `web/index.html` mostra una didascalia `Durata: sposta lo slider` sopra la barra delle card zona per chiarire la modifica minuti.
- 2026-08-31: bump versione a `10.5.22`; rilascio coordinato con il custom component e-Dry `10.1.4` thread-safe.
