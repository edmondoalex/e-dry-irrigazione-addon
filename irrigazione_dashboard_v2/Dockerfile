FROM python:3.12-alpine

WORKDIR /app

# dipendenze
RUN pip install flask requests websocket-client

# copia script e statici
COPY run.sh /run.sh
COPY web /app/web

RUN chmod a+x /run.sh

# esponi dashboard (1977) e debug entit╚ (1978)
EXPOSE 1977 1978

CMD ["/run.sh"]
