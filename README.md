# Nogalix API

FastAPI + SQLAlchemy + Alembic + Pydantic + MySQL.

## Stack

- FastAPI / Uvicorn
- MySQL (`nogalix`)
- Alembic migrations
- Opaque Bearer tokens (style Sanctum)
- Cloudinary (avatars / audio)
- Gemini (assistant, avec repli local)

## Architecture

```
app/
  core/          config, db, security, deps, responses
  support/       cloudinary, google auth
  modules/       auth, cv, profile, notifications, assistant, contact, health, templates
alembic/
```

Pas de gestion de droits / RBAC (volontairement, vs CBC).

Les **layouts de modèles CV** restent dans le frontend ; le backend stocke les **données** (`templateId` + payload JSON).

## Démarrage

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8010
```

> Port `8000`/`8001` peuvent être pris par Cursor en local — `8010` est le port recommandé.

API : `http://localhost:8010/api`  
Docs : `http://localhost:8010/docs`

Frontend : `NEXT_PUBLIC_API_URL=http://localhost:8010/api`
