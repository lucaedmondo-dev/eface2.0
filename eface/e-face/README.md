# e-face

Questo repository contiene un add-on sperimentale chiamato `e-face`: una interfaccia utente completamente personalizzata per il controllo del sistema.

Caratteristiche incluse in questa scaffolding:

- Frontend: Vue 3 + Vite (interfaccia demo con login, dashboard e impostazioni avanzate)
- Backend (opzionale): FastAPI che fornisce autenticazione token, endpoint di configurazione e serve i file statici del frontend
- Dockerfile per creare un'immagine che costruisce il frontend e avvia il backend (per test come container)
- `docker-compose.yml` per avviare in locale in modo rapido

Eseguire in locale (PowerShell):

1) Avviare il backend e frontend in sviluppo separati:

```
# nella cartella backend
python -m venv .venv; .\.venv\Scripts\Activate; pip install -r requirements.txt; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# nella cartella frontend
cd frontend; npm install; npm run dev
```

2) Eseguire via Docker Compose (costruisce l'immagine che include frontend built):

```
docker compose build
docker compose up
```

Add-on note:
- Aggiunto `run.sh` per avviare l'API quando installato come add-on/container.

## HTTPS e reverse proxy automatico

L'immagine dell'add-on ora include Caddy come reverse proxy frontale:

- FastAPI gira internamente su `127.0.0.1:9000`.
- Caddy espone l'istanza su `:8000` in HTTP e, opzionalmente, su 443 in HTTPS.
- I certificati e lo stato di Caddy vengono salvati in `/data/caddy`, così i rinnovi sopravvivono ai riavvii dell'add-on.

### Opzioni dell'add-on

Nel `config.json` sono disponibili tre chiavi:

| Opzione | Default | Descrizione |
| --- | --- | --- |
| `https_enabled` | `false` | Se `true`, genera un blocco HTTPS in Caddy e innesca l'emissione di certificati automatici. |
| `https_domain` | `""` | Dominio pubblico da proteggere (es. `manager.ekonex.it`). Obbligatorio quando abiliti HTTPS. |
| `https_email` | `""` | Email da passare a Let's Encrypt (opzionale ma consigliata per notifiche di rinnovo). |

Una volta impostate le opzioni e mappata la porta 443 dell'host verso il container, il processo di installazione/certificazione è completamente automatico. Se lasci `https_enabled` a `false`, l'add-on continuerà a rispondere solo su HTTP (porta 8000) e potrai usarlo in LAN o tramite tunnel TCP.
