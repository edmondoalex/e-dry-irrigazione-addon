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
- Versione corrente prototipo: `10.1.0`.

Meteo
- La dashboard legge i dati da e-SunMind tramite `e_sunmind_api_url`.
- Default: `http://192.168.3.24:1980/api/weather/irrigation`.
- Se l'URL non e raggiungibile, usa come fallback i sensori Home Assistant `sensor.e_sunmind_weather_*`.

Tarature meteo
- Dal menu della dashboard apri `Tarature meteo`.
- La sezione e protetta da `admin_settings_password`, da configurare nelle opzioni dell'add-on.
- La fonte primaria e l'endpoint e-SunMind `/api/weather/irrigation`.
- I sensori mostrati come `fallback` vengono usati solo se e-SunMind non risponde o il dato non e fresco.
- Puoi modificare SmartCalc, freschezza dato, soglie pioggia prevista/recente, vento e gelo direttamente dall'add-on.
- Le entita fallback sono visibili solo come diagnostica e non sono modificabili dalla dashboard cliente.

Preset zone
- Dal popup admin `Tarature meteo` puoi assegnare un preset comportamento a ogni zona.
- Preset integrati dal component: `standard`, `erba`, `fiori`, `piante`, `orto`, `vasi`, `alberi`.
- Puoi creare preset custom con nome, moltiplicatore SmartCalc e flag vento.
- La dashboard salva tutto nel component e-Dry tramite `e_dry.update_zone` e `e_dry.update_zone_profiles`.
- Persistenza: preset custom e assegnazioni zona sono nelle opzioni del config entry Home Assistant, quindi restano dopo restart add-on e Home Assistant.
- Il popup admin usa scroll interno, cosi puoi raggiungere tutti i campi e i pulsanti senza far scorrere la pagina principale.

Se vuoi che prepari un pacchetto release pronto per essere distribuito (zip con changelog e README), dimmelo.




































































































