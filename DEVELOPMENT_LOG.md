# Development log

## 2026-06-03

- Creato repository installabile Home Assistant con `repository.json` in root.
- Spostato l'add-on nella cartella `irrigazione_dashboard_v2/`, come richiesto dallo store add-on.
- Esclusi dati runtime, cache, log, backup locali e pacchetti zip tramite `.gitignore`.
- Conservati i file sorgente essenziali: `config.yaml`, `Dockerfile`, `run.sh`, `web/`, immagini, README e changelog dell'add-on.
- Corretto `restart_addon.sh` per usare la cartella reale `irrigazione_dashboard_v2` e lanciare `run.sh` dalla root dell'add-on.
