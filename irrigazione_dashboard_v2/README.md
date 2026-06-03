# Irrigazione Dashboard add-on

Questa Ã¨ una versione modificata e stabile dell'add-on "Irrigazione Dashboard".

FunzionalitÃ  principali:
- Dashboard web per avviare/fermare le zone di irrigazione
- Discovery delle zone da integrazione `e-dry` (se configurata)
- Supporto per mostrare valori di produzione/percentuali e durate

Installazione e test
1. Copia la cartella `irrigazione_dashboard_v2` in `addons/local/` del tuo Home Assistant.
2. Vai in Supervisor â†’ Add-on Store â†’ My add-ons â†’ Irrigazione Dashboard e installa.
3. Se usi il componente `e-dry`, imposta `bind_config_entry_id` nelle opzioni dell'add-on
   con il `config_entry_id` dell'integrazione (vedi le istruzioni UI nel changelog).
4. Riavvia l'addâ€‘on e apri la dashboard su `http://<HA_IP>:1977`.

Opzioni importanti (config.yaml)
- `auth_mode`: none|basic|key â€” modalitÃ  di autenticazione per la dashboard
- `bind_config_entry_id`: se valorizzato, il server userÃ  l'entity registry per scoprire le entitÃ 

Debug e log
- I log dell'add-on sono disponibili tramite Supervisor â†’ Add-on â†’ Logs.
- L'integrazione `e-dry` scrive inoltre i suoi debug in `config/custom_components/e-dry_irrigation/e_dry_debug.log`.

Note
- Versione corrente: `10.0.1`.

Se vuoi che prepari un pacchetto release pronto per essere distribuito (zip con changelog e README), dimmelo.




































































































