# syntax=docker/dockerfile:1

FROM python:3.11-slim

WORKDIR /app

# Installazione requirements backend
COPY e-face/backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Codice backend + frontend compilato
COPY e-face/backend/ ./backend/
COPY e-face/frontend_dist/ ./frontend_dist/

# Script di avvio custom
COPY run.sh /run.sh
RUN chmod +x /run.sh

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["/run.sh"]
