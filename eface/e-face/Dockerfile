# syntax=docker/dockerfile:1

FROM python:3.11-slim

WORKDIR /app

# (opzionale) pacchetti di sistema, se ti servono per i requirements
# RUN apt-get update && apt-get install -y \
#     build-essential \
#  && rm -rf /var/lib/apt/lists/*

# 1) Copio SOLO il file dei requisiti del backend
#    (adatta il nome se non è requirements.txt)
COPY e-face/backend/requirements.txt ./backend/requirements.txt

# 2) Installo i requisiti Python
RUN pip install --no-cache-dir -r backend/requirements.txt

# 3) Copio tutto il backend
COPY e-face/backend/ ./backend/

# 4) Copio il frontend già compilato (separato)
#    Se il backend lo ha già dentro di sé, questa parte la puoi togliere
COPY e-face/frontend_dist/ ./frontend_dist/

# 5) Copio lo script di avvio dell'addon
COPY run.sh /run.sh
RUN chmod +x /run.sh

# 6) Comando di avvio
CMD ["/run.sh"]
