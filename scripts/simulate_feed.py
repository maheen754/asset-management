"""
Simulates an AUTOMATED system pushing assets into the register
(e.g. a barcode scanner gateway, ERP export or camera pipeline).

Usage:
    INGEST_API_KEY=secret python app.py              # start the server (other terminal)
    INGEST_API_KEY=secret python scripts/simulate_feed.py [http://localhost:5000] [count]
Needs Pillow (already in backend/requirements.txt). No other libraries.
"""
import base64
import io
import json
import os
import random
import sys
import urllib.request

from PIL import Image, ImageDraw

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
COUNT = int(sys.argv[2]) if len(sys.argv) > 2 else 6
KEY = os.environ.get("INGEST_API_KEY", "")
CATEGORIES = ["Pallet", "Forklift", "Rack", "Container", "Electronics", "Tool", "Vehicle", "Other"]
COLORS = [(190, 140, 60), (70, 110, 130), (150, 150, 140), (120, 80, 70), (90, 120, 90)]


def fake_photo(label):
    img = Image.new("RGB", (800, 600), random.choice(COLORS))
    ImageDraw.Draw(img).text((30, 30), label, fill="white")
    buf = io.BytesIO()
    img.save(buf, "JPEG")
    return base64.b64encode(buf.getvalue()).decode()


assets = []
for _ in range(COUNT):
    cat = random.choice(CATEGORIES)
    asset_id = f"{cat[:3].upper()}-{random.randint(1000, 9999)}"
    assets.append({"asset_id": asset_id, "category": cat, "photo_base64": fake_photo(asset_id)})

req = urllib.request.Request(
    f"{BASE}/api/assets/ingest",
    data=json.dumps({"assets": assets}).encode(),
    headers={"Content-Type": "application/json", "X-API-Key": KEY},
    method="POST",
)
with urllib.request.urlopen(req) as res:
    print(res.status, res.read().decode())