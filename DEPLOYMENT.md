# Vercel deployment

This repository deploys as one Vercel project using Vercel Services. Keep the
Vercel project root at the repository root so `vercel.json` can build the Vite
frontend from `frontend/` and Django from `backend/`. Use Vercel CLI 50.38.0 or
newer for local service deployments.

The shared domain routes `/api/`, `/admin/`, and `/static/` to Django. Other
paths go to the React SPA, including deep links. In production, the frontend
uses the same-origin `/api` endpoint by default. `VITE_API_BASE_URL` can
override this; local development retains the `127.0.0.1:8000` default.

Configure these Vercel project environment variables:

- `DJANGO_SECRET_KEY`: a unique, securely generated secret.
- `DEBUG`: `False`.
- `ALLOWED_HOSTS`: comma-separated custom hostnames, without schemes. Vercel's
  `VERCEL_URL` hostname is added automatically.
- `DATABASE_URL`: a managed PostgreSQL connection URL. Vercel Functions have
  ephemeral filesystems, so the local SQLite database is only a development
  fallback and must not be used for production data.

Apply Django migrations to the production database before using the API:

```powershell
cd backend
python manage.py migrate
```

Run the migration with the production `DATABASE_URL` available in the
environment. Vercel’s Django runtime detects `manage.py` and the WSGI/ASGI
application; Django static files are collected from `STATIC_ROOT`.
