# Development log

## 2026-06-03

- Creato repository installabile Home Assistant con `repository.json` in root.
- Spostato l'add-on nella cartella `irrigazione_dashboard_v2/`, come richiesto dallo store add-on.
- Esclusi dati runtime, cache, log, backup locali e pacchetti zip tramite `.gitignore`.
- Conservati i file sorgente essenziali: `config.yaml`, `Dockerfile`, `run.sh`, `web/`, immagini, README e changelog dell'add-on.
- Corretto `restart_addon.sh` per usare la cartella reale `irrigazione_dashboard_v2` e lanciare `run.sh` dalla root dell'add-on.
- Check globale: bump a `10.0.1`, versioni runtime allineate e riferimenti legacy corretti.
- Meteo migrato a e-SunMind: aggiunta opzione `e_sunmind_api_url`, dashboard alimentata da `/api/data`, fallback OpenWeather non piu usato.
- Meteo irrigazione allineato al nuovo contratto e-SunMind `/api/weather/irrigation`; bump add-on a `10.0.3`.
- Aggiunta gestione tarature meteo da dashboard: endpoint `/api/meteo/weather_settings`, popup UI e salvataggio tramite servizio component `e_dry.update_weather_settings`; bump add-on a `10.0.4`.
- Protetta la sezione tarature meteo con `admin_settings_password`, rimossa modifica entita fallback dalla dashboard cliente; bump add-on a `10.0.5`.
- Bump add-on a `10.0.6`: aggiunta gestione admin preset zona e preset custom persistenti tramite `/api/irrigazione/zone_profiles` e servizi component `e_dry.update_zone`/`e_dry.update_zone_profiles`.
- Bump add-on a `10.0.7`: corretto popup admin con scroll interno e blocco scroll pagina sottostante.

## 2026-06-04

- Bump add-on a `10.0.8`: ripristinata icona hamburger del menu con tre barre HTML/CSS indipendenti dalla codifica.
- Bump add-on a `10.0.9`: aggiunto logo EKONEX traslucido al centro dell'intestazione della card meteo.
- Bump add-on a `10.0.10`: aggiunta route HTTP dedicata al logo EKONEX per correggerne il caricamento.
- Creati tag `backup-before-controller-ui-20260604` e branch `codex/controller-ui-prototype` per una prova UI completamente reversibile.
- Bump prototipo add-on a `10.1.0`: aggiunta panoramica operativa e nuova gerarchia visiva stile centralina professionale.
- Bump prototipo add-on a `10.1.1`: corretto lo sfondo full viewport evitando la ripetizione a quadrati.
- Bump prototipo add-on a `10.2.0`: aggiunti riepiloghi prossima irrigazione e decisione SmartCalc.
- Bump prototipo add-on a `10.2.1`: portate le scritte finali delle zone sopra la decorazione sprinkler.
- Bump prototipo add-on a `10.2.2`: spostato fisicamente lo sprinkler sotto le scritte e nascosto nelle zone OFF.

## 2026-06-05

- Bump prototipo add-on a `10.3.0`: ripulite card zona con badge preset e metriche durata compatte.
- Bump prototipo add-on a `10.3.1`: corretto layout badge zona a due colonne per evitare tagli nelle card strette.
- Bump prototipo add-on a `10.3.2`: reso stabile il pulsante Modifica programmi sospendendo il refresh durante l'editing.
- Bump prototipo add-on a `10.4.0`: aggiunta creazione programmi da dashboard add-on tramite servizio component `e_dry.create_program`.
