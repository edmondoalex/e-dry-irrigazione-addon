# e-Dry Irrigazione add-on repository

Repository Home Assistant per l'add-on Supervisor `e-Dry Irrigazione`.

## Installazione in Home Assistant

1. Apri Home Assistant.
2. Vai in **Settings > Add-ons > Add-on Store**.
3. Apri il menu in alto a destra e scegli **Repositories**.
4. Aggiungi questo repository:

   `https://github.com/edmondoalex/e-dry-irrigazione-addon`

5. Installa l'add-on **e-Dry Irrigazione**.

## Add-on incluso

- `irrigazione_dashboard_v2`
- Porta dashboard: `1977`
- Porta debug entita: `1978`
- Ingress Home Assistant: abilitato

## Dipendenza funzionale

La dashboard usa il custom component `e_dry`, pubblicato separatamente nel repository:

`https://github.com/edmondoalex/e-dry-irrigation-component`

Il collegamento avviene tramite l'opzione `bind_config_entry_id` e tramite i servizi Home Assistant `e_dry.start_zone`, `e_dry.stop_zone`, `e_dry.update_zone` e `e_dry.update_program`.
