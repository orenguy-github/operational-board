#!/usr/bin/env python3
"""
AISStream proxy for Ashdod Port forecast.
Connects to AISStream WebSocket, filters vessels near Ashdod or with destination Ashdod,
and serves a simple JSON endpoint for the operational board.
"""
import asyncio
import json
import os
import time
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS
from threading import Thread
import websockets

# Ashdod approximate bounding box (expand as needed)
ASHDOD_BBOX = [[31.6, 34.4], [32.1, 34.9]]  # [lat1, lon1], [lat2, lon2]

API_KEY = os.environ.get("AISSTREAM_API_KEY", "")
if not API_KEY:
    print("WARNING: Set AISSTREAM_API_KEY environment variable")

# In-memory store of relevant vessels
vessels = {}  # mmsi -> data
last_update = 0

def is_relevant(msg):
    """Filter for ships that might be heading to or near Ashdod."""
    meta = msg.get("MetaData", {})
    name = meta.get("ShipName", "").upper()
    dest = ""
    # Look for destination in various message types
    message = msg.get("Message", {})
    for key in message:
        if isinstance(message[key], dict):
            dest = message[key].get("Destination", dest) or dest
    dest = (dest or "").upper()
    lat = meta.get("Latitude")
    lon = meta.get("Longitude")
    # Near Ashdod or destination mentions Ashdod / ILASH
    near = False
    if lat and lon:
        near = 31.6 <= lat <= 32.1 and 34.4 <= lon <= 34.9
    dest_match = "ASHDOD" in dest or "ILASH" in dest or "IL ASD" in dest
    return near or dest_match or "ASHDOD" in name

async def ais_listener():
    global vessels, last_update
    uri = "wss://stream.aisstream.io/v0/stream"
    # Wider box around Israel coast for better chance of signals
    sub = {
        "APIKey": API_KEY,
        "BoundingBoxes": [[[31.0, 34.0], [33.0, 35.5]]],
        "FilterMessageTypes": ["PositionReport", "ShipStaticData", "StandardClassBPositionReport"]
    }
    while True:
        try:
            print("Connecting to AISStream...", flush=True)
            async with websockets.connect(uri) as ws:
                await ws.send(json.dumps(sub))
                print("Connected and subscribed to area around Ashdod", flush=True)
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                        if not is_relevant(msg):
                            continue
                        meta = msg.get("MetaData", {})
                        mmsi = str(meta.get("MMSI", ""))
                        if not mmsi:
                            continue
                        name = meta.get("ShipName", "Unknown").strip()
                        lat = meta.get("Latitude")
                        lon = meta.get("Longitude")
                        sog = None
                        cog = None
                        dest = ""
                        eta_raw = None
                        message = msg.get("Message", {})
                        for k, v in message.items():
                            if isinstance(v, dict):
                                sog = v.get("Sog", sog)
                                cog = v.get("Cog", cog)
                                dest = v.get("Destination", dest) or dest
                                eta_raw = v.get("Eta") or v.get("ETA") or eta_raw
                        eta_str = "—"
                        if isinstance(eta_raw, dict):
                            try:
                                eta_str = f"{eta_raw.get('Day',0):02d}.{eta_raw.get('Month',0):02d} · {eta_raw.get('Hour',0):02d}:{eta_raw.get('Minute',0):02d}"
                            except:
                                eta_str = str(eta_raw)
                        elif eta_raw:
                            eta_str = str(eta_raw)
                        vessels[mmsi] = {
                            "id": f"ais_{mmsi}",
                            "mmsi": mmsi,
                            "name": name,
                            "flag": "",
                            "imo": "",
                            "origin": (dest or "—").strip(),
                            "eta": eta_str,
                            "berth": "",
                            "agent": "",
                            "lat": lat,
                            "lon": lon,
                            "sog": sog,
                            "cog": cog,
                            "last_seen": datetime.utcnow().isoformat() + "Z"
                        }
                        last_update = time.time()
                        print(f"Updated vessel: {name} ({mmsi})", flush=True)
                    except Exception as e:
                        print("Parse error:", e, flush=True)
        except Exception as e:
            print("AISStream connection error:", e, flush=True)
            await asyncio.sleep(10)

def run_ais():
    asyncio.run(ais_listener())

app = Flask(__name__)
CORS(app)  # Allow browser requests from the HTML file

import os
HTML_PATH = os.path.join(os.path.dirname(__file__), "ashdod-operational-board.html")

@app.route("/")
def index():
    with open(HTML_PATH, encoding="utf-8") as f:
        return f.read()
def forecast():
    # Return list of vessels, newest first
    items = list(vessels.values())
    items.sort(key=lambda x: x.get("last_seen", ""), reverse=True)
    return jsonify({
        "updated": datetime.utcfromtimestamp(last_update).isoformat() + "Z" if last_update else None,
        "count": len(items),
        "ships": items
    })

@app.route("/health")
def health():
    return jsonify({"ok": True, "vessels": len(vessels), "has_key": bool(API_KEY)})

if __name__ == "__main__":
    if API_KEY:
        Thread(target=run_ais, daemon=True).start()
    else:
        print("No API key – serving empty forecast. Set AISSTREAM_API_KEY to enable.")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
