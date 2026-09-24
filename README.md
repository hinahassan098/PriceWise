# PriceWise

Grocery price comparison across Pakistani online stores.

## Live URLs

| Surface | URL |
|--------|-----|
| Web | https://pricewise-78on.onrender.com |
| API | https://pricewise-api-dauj.onrender.com |
| API docs | https://pricewise-api-dauj.onrender.com/docs |
| Android APK | Desktop `PriceWise.apk` |

## Project layout

- `backend/` — FastAPI + live Shopify search
- `web/` — Next.js UI
- `mobile/` — Expo React Native app
- `render.yaml` — Render blueprint

## One remaining Render step (Admin Collect)

Admin collect is locked until you set a shared secret:

1. Open https://dashboard.render.com and sign in.
2. API service (`pricewise-api-dauj`) → Environment → add `ADMIN_API_KEY` = a long random string.
3. Web service (`pricewise-78on`) → Environment → add the **same** `ADMIN_API_KEY`.
4. Confirm web has `NEXT_PUBLIC_API_URL=https://pricewise-api-dauj.onrender.com`.
5. Save (auto-redeploy).

Without the key, unauthenticated collect returns **503** (safe). With the key configured, open `/admin`, paste the key into **Admin API key**, then run Collect. The browser must send `X-Admin-Key`; anonymous `POST /api/admin/collect-all` returns **401**.

## Local development

```bash
# API
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Web
cd web
npm install
npm run dev

# Mobile API smoke (no device)
cd mobile
node scripts/mobile-smoke.mjs
```

## Mobile

```bash
cd mobile
npm install
npm run android
```

Install `PriceWise.apk` from the Desktop onto an Android phone (allow unknown sources).
