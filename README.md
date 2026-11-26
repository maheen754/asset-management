# Warehouse Asset Register

A small full-stack prototype for a warehouse: operators register assets (ID, category, photo) from a PC or a phone, the records are stored on an on-premises server, and everyone on the local network can browse and search them.

Manual entry can later be replaced by an automated system: a separate machine-to-machine endpoint (`POST /api/assets/ingest`) already exists and is demonstrated by `scripts/simulate_feed.py`.


## Features

- Form with Asset ID, Asset Category (dropdown) and Asset Photo (upload; phones can use the camera)
- Records stored in SQLite through a REST API; photos stored on the server disk
- Dashboard listing all records (newest first, paginated) with a category filter
- Search by Asset ID (partial match, case-insensitive)
- Record page with the full-size photo
- Responsive layout: two columns on desktop, single column on phone
- Validation on both client and server; duplicate IDs are rejected with a clear message
- API-key protected endpoint for automated data; each record keeps its `source` (`manual` or `automated`)

## Tech stack

| Part | Choice | Reason |
|---|---|---|
| Frontend | React 18 + Vite | Small static build, no extra UI library needed |
| Backend | Python Flask | Simple, readable REST API |
| Database | SQLite | Zero-install, a single file, fine for one warehouse PC |
| Photos | Files on disk, filename in DB | Keeps the database small and fast |

## Architecture

```
 Phone / PC browser  ─────────┐
 Phone / PC browser  ─────────┼──►  Flask (0.0.0.0:5000)  ──►  SQLite (backend/assets.db)
                              │      ├─ serves the built React app    └─ uploads/ (photos)
 Automated system  ───────────┘      ├─ /api/...      REST endpoints
 (scanner, ERP, camera...)           └─ /uploads/...  photos
        POST /api/assets/ingest (X-API-Key)
```

In production, Flask serves the built React app, so the server PC runs one process on one port.


## Project structure

```
backend/
  app.py                 Flask app: schema, validation, image handling, endpoints
  requirements.txt
frontend/
  src/api.js             all network calls
  src/App.jsx            layout + small hash router
  src/components/        AssetForm, AssetList, AssetDetail
  src/styles.css         responsive styles
scripts/simulate_feed.py simulates an automated system pushing records
```

## How to run

Requirements: Python 3.10+ and Node.js 18+.

### 1. Build the frontend

```bash
cd frontend
npm install
npm run build
```

### 2. Start the backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000` on the same PC.

### 3. Open it from a phone or another PC

1. Connect the device to the same Wi-Fi/LAN as the server PC.
2. Find the server's IP address: `ipconfig` (Windows) or `ip addr` (Linux).
3. Allow TCP port 5000 in the firewall (Windows, run as Administrator):
   ```
   netsh advfirewall firewall add rule name="AssetTracker" dir=in action=allow protocol=TCP localport=5000
   ```
4. On the phone open `http://<server-ip>:5000`, for example `http://192.168.1.20:5000`.

### Development mode (hot reload)

```bash
# terminal 1
cd backend && python app.py
# terminal 2
cd frontend && npm run dev        # http://localhost:5173
```

Vite proxies `/api` and `/uploads` to Flask, so no CORS setup is needed.

### Try the automated feed

```powershell
# terminal 1 (PowerShell): start the server with an API key
$env:INGEST_API_KEY="secret"
cd backend
python app.py

# terminal 2: push 6 generated assets with photos
$env:INGEST_API_KEY="secret"
python scripts/simulate_feed.py http://localhost:5000 6
```

On Linux/macOS use `INGEST_API_KEY=secret python app.py`. Refresh the dashboard; the new records show "Entered by: Automated system".

### Configuration

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | `5000` | server port |
| `ASSET_DB` | `backend/assets.db` | SQLite file location |
| `ASSET_UPLOADS` | `backend/uploads` | photo folder |
| `INGEST_API_KEY` | empty (ingest disabled) | secret for the automated endpoint |

## REST API

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | liveness check |
| GET | `/api/categories` | allowed categories |
| GET | `/api/assets?q=&category=&page=&per_page=` | list / search (`q` = partial Asset ID) |
| GET | `/api/assets/<asset_id>` | one record |
| POST | `/api/assets` | create (multipart: `asset_id`, `category`, `photo`) |
| DELETE | `/api/assets/<asset_id>` | delete a record and its photo |
| POST | `/api/assets/ingest` | automated upsert, header `X-API-Key` |
Ingest example:

```bash
curl -X POST http://localhost:5000/api/assets/ingest \
  -H "X-API-Key: secret" -H "Content-Type: application/json" \
  -d '{"assets":[{"asset_id":"PLT-900","category":"Pallet"}]}'
```

`photo_base64` is optional for each item. The response reports `created`, `updated` and per-item `errors`, so one bad row does not reject the whole batch.

## Database design

```sql
assets(
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_id       TEXT NOT NULL UNIQUE COLLATE NOCASE,  -- business ID, "plt-1" == "PLT-1"
  category       TEXT NOT NULL,
  photo_filename TEXT,                                  -- file in uploads/
  source         TEXT NOT NULL DEFAULT 'manual',        -- 'manual' | 'automated'
  created_at     TEXT NOT NULL,                         -- UTC ISO-8601
  updated_at     TEXT NOT NULL
)
```

A surrogate `id` plus a unique business `asset_id` allows the business ID to be corrected later without breaking references. Indexes cover category filtering and newest-first ordering.

## Design decisions

- **Image handling:** uploads are verified with Pillow (a renamed text file is rejected), rotated according to EXIF so phone photos are upright, resized to at most 1600 px and saved as JPEG under a random UUID filename. Request size is capped at 12 MB.
- **Safe queries:** all SQL is parameterised and `LIKE` wildcards in the search text are escaped.
- **Race safety:** the UNIQUE constraint is the final guard if two operators save the same ID at the same moment.
- **Replacing manual entry:** storage and UI do not care where a record came from. Automation only needs the ingest endpoint, and both paths share the same validation.
- **Network:** a single origin (Flask serves everything), so phones need one URL and there are no CORS issues.

## Limitations and next steps

This is a prototype, so it intentionally leaves out:

- User login and roles (only the ingest endpoint uses an API key). Next step: operator accounts and HTTPS behind a reverse proxy.
- Editing a record from the UI.
- Automated tests and CI.
- A move to PostgreSQL if several services write heavily at once.
