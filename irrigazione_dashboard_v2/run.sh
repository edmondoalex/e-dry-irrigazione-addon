#!/bin/sh
set -e

cd /app/web

# Avvia il server di debug entità (porta 1978 o quella impostata in options.json)
python3 entities_server.py &

# Avvia la dashboard principale (porta 1977)
python3 server.py
