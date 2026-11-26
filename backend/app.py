
import base64
import binascii
import hmac
import io
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, g, jsonify, request, send_from_directory
from PIL import Image, ImageOps, UnidentifiedImageError

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("ASSET_DB", BASE_DIR / "assets.db"))
UPLOAD_DIR = Path(os.environ.get("ASSET_UPLOADS", BASE_DIR / "uploads"))
DIST_DIR = BASE_DIR.parent / "frontend" / "dist"

INGEST_API_KEY = os.environ.get("INGEST_API_KEY", "")

CATEGORIES = ["Pallet", "Forklift", "Rack", "Container", "Electronics", "Tool", "Vehicle", "Other"]
ASSET_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
MAX_IMAGE_SIDE = 1600

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024  # 12 MB per request
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# database
SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id       TEXT NOT NULL UNIQUE COLLATE NOCASE,   -- business identifier
    category       TEXT NOT NULL,
    photo_filename TEXT,
    source         TEXT NOT NULL DEFAULT 'manual',        -- 'manual' | 'automated'
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_assets_category ON assets(category);
CREATE INDEX IF NOT EXISTS idx_assets_created  ON assets(created_at DESC);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.executescript(SCHEMA)


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def row_to_dict(row):
    return {
        "id": row["id"],
        "asset_id": row["asset_id"],
        "category": row["category"],
        "photo_url": f"/uploads/{row['photo_filename']}" if row["photo_filename"] else None,
        "source": row["source"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


#  helpers
class ApiError(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status


@app.errorhandler(ApiError)
def handle_api_error(err):
    return jsonify(error=err.message), err.status


@app.errorhandler(413)
def too_large(_err):
    return jsonify(error="Photo is too large (max 12 MB)."), 413


def validate_fields(asset_id, category):
    asset_id = (asset_id or "").strip()
    category = (category or "").strip()
    if not ASSET_ID_RE.match(asset_id):
        raise ApiError("Asset ID must be 1-64 characters: letters, numbers, dot, dash or underscore.")
    if category not in CATEGORIES:
        raise ApiError("Pick a valid asset category.")
    return asset_id, category


def save_image(raw: bytes) -> str:
    """Verify it is really an image, fix phone rotation, shrink, store as JPEG."""
    try:
        Image.open(io.BytesIO(raw)).verify()
        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img)
    except (UnidentifiedImageError, OSError):
        raise ApiError("The uploaded file is not a valid image.")
    if img.mode != "RGB":
        rgba = img.convert("RGBA")
        img = Image.new("RGB", rgba.size, "white")
        img.paste(rgba, mask=rgba.split()[-1])
    img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
    name = f"{uuid.uuid4().hex}.jpg"
    img.save(UPLOAD_DIR / name, "JPEG", quality=85, optimize=True)
    return name


def delete_image(filename):
    if filename:
        try:
            (UPLOAD_DIR / filename).unlink()
        except FileNotFoundError:
            pass


#  REST API
@app.get("/api/health")
def health():
    return jsonify(status="ok")


@app.get("/api/categories")
def categories():
    return jsonify(CATEGORIES)


@app.get("/api/assets")
def list_assets():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 12, type=int), 1), 100)

    where, params = [], []
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where.append("asset_id LIKE ? ESCAPE '\\'")
        params.append(f"%{escaped}%")
    if category:
        where.append("category = ?")
        params.append(category)
    clause = f"WHERE {' AND '.join(where)}" if where else ""

    db = get_db()
    total = db.execute(f"SELECT COUNT(*) FROM assets {clause}", params).fetchone()[0]
    rows = db.execute(
        f"SELECT * FROM assets {clause} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
        params + [per_page, (page - 1) * per_page],
    ).fetchall()
    return jsonify(items=[row_to_dict(r) for r in rows], total=total, page=page, per_page=per_page)


@app.get("/api/assets/<asset_id>")
def get_asset(asset_id):
    row = get_db().execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
    if not row:
        raise ApiError("Asset not found.", 404)
    return jsonify(row_to_dict(row))


@app.post("/api/assets")
def create_asset():
    """Manual entry from the dashboard (multipart/form-data)."""
    asset_id, category = validate_fields(request.form.get("asset_id"), request.form.get("category"))
    photo = request.files.get("photo")
    if not photo or not photo.filename:
        raise ApiError("Please attach a photograph of the asset.")

    db = get_db()
    if db.execute("SELECT 1 FROM assets WHERE asset_id = ?", (asset_id,)).fetchone():
        raise ApiError(f"Asset ID '{asset_id}' already exists.", 409)

    filename = save_image(photo.read())
    ts = now_iso()
    try:
        db.execute(
            "INSERT INTO assets (asset_id, category, photo_filename, source, created_at, updated_at) "
            "VALUES (?, ?, ?, 'manual', ?, ?)",
            (asset_id, category, filename, ts, ts),
        )
        db.commit()
    except sqlite3.IntegrityError:  
        delete_image(filename)
        raise ApiError(f"Asset ID '{asset_id}' already exists.", 409)
    row = db.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
    return jsonify(row_to_dict(row)), 201


@app.delete("/api/assets/<asset_id>")
def delete_asset(asset_id):
    db = get_db()
    row = db.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
    if not row:
        raise ApiError("Asset not found.", 404)
    db.execute("DELETE FROM assets WHERE id = ?", (row["id"],))
    db.commit()
    delete_image(row["photo_filename"])
    return jsonify(deleted=row["asset_id"])


@app.post("/api/assets/ingest")
def ingest_assets():
   
    supplied = request.headers.get("X-API-Key", "")
    if not INGEST_API_KEY or not hmac.compare_digest(supplied, INGEST_API_KEY):
        raise ApiError("Invalid or missing API key.", 401)

    payload = request.get_json(silent=True) or {}
    items = payload.get("assets")
    if not isinstance(items, list) or not items:
        raise ApiError('Body must be {"assets": [ ... ]}.')

    db = get_db()
    results = {"created": 0, "updated": 0, "errors": []}
    for i, item in enumerate(items):
        try:
            asset_id, category = validate_fields(item.get("asset_id"), item.get("category"))
            new_file = None
            if item.get("photo_base64"):
                try:
                    new_file = save_image(base64.b64decode(item["photo_base64"], validate=True))
                except (binascii.Error, ValueError):
                    raise ApiError("photo_base64 is not valid base64.")
            existing = db.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
            ts = now_iso()
            if existing:
                db.execute(
                    "UPDATE assets SET category = ?, photo_filename = ?, source = 'automated', updated_at = ? WHERE id = ?",
                    (category, new_file or existing["photo_filename"], ts, existing["id"]),
                )
                if new_file:
                    delete_image(existing["photo_filename"])
                results["updated"] += 1
            else:
                db.execute(
                    "INSERT INTO assets (asset_id, category, photo_filename, source, created_at, updated_at) "
                    "VALUES (?, ?, ?, 'automated', ?, ?)",
                    (asset_id, category, new_file, ts, ts),
                )
                results["created"] += 1
        except (ApiError, AttributeError) as err:
            msg = err.message if isinstance(err, ApiError) else "Each asset must be an object."
            results["errors"].append({"index": i, "error": msg})
    db.commit()
    return jsonify(results), 207 if results["errors"] else 200


# files + web frontend
@app.get("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(UPLOAD_DIR, filename, max_age=31536000)


@app.get("/", defaults={"path": ""})
@app.get("/<path:path>")
def frontend(path):
    if path.startswith("api/"):
        raise ApiError("Endpoint not found.", 404)
    if not DIST_DIR.exists():
        return ("Frontend not built yet. Run `npm run build` in /frontend "
                "or use the dev server (npm run dev).", 200)
    target = DIST_DIR / path
    if path and target.is_file():
        return send_from_directory(DIST_DIR, path)
    return send_from_directory(DIST_DIR, "index.html")


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Asset Tracker API running on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)