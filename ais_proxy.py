#!/usr/bin/env python3
"""
AISStream proxy for Ashdod Port forecast.
Serves both the operational board HTML and the /forecast API.
"""
import asyncio
import json
import os
import time
from datetime import datetime, timezone
from flask import Flask, jsonify
from flask_cors import CORS
from threading import Thread
import websockets

API_KEY = os.environ.get("AISSTREAM_API_KEY", "")
if not API_KEY:
    print("WARNING: Set AISSTREAM_API_KEY environment variable")

vessels = {}
last_update = 0

def is_relevant(msg):
    meta = msg.get("MetaData", {})
    name = meta.get("ShipName", "").upper()
    dest = ""
    message = msg.get("Message", {})
    for key in message:
        if isinstance(message[key], dict):
            dest = message[key].get("Destination", dest) or dest
    dest = (dest or "").upper()
    lat = meta.get("Latitude")
    lon = meta.get("Longitude")
    near = False
    if lat and lon:
        near = 31.6 <= lat <= 32.1 and 34.4 <= lon <= 34.9
    dest_match = "ASHDOD" in dest or "ILASH" in dest or "IL ASD" in dest
    return near or dest_match or "ASHDOD" in name

async def ais_listener():
    global vessels, last_update
    uri = "wss://stream.aisstream.io/v0/stream"
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
                        sog = cog = None
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
                            "last_seen": datetime.now(timezone.utc).isoformat()
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
CORS(app)

HTML = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>מסך מבצעי — מעבר גבול ימי אשדוד</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Rubik:wght@500;700;900&family=Heebo:wght@300;400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet">
<style>
  :root{--bg-deep:#f4f7fb;--bg-panel:#ffffff;--bg-panel-raised:#f0f4f8;--line:#d0d7e2;--line-soft:#e2e8f0;--text-hi:#1a2332;--text-mid:#4a5568;--text-low:#718096;--teal:#0d9488;--teal-dim:#0f766e;--amber:#d97706;--red:#dc2626;--blue:#2563eb;--radius:10px;}
  *{box-sizing:border-box;margin:0;padding:0;}
  body{background:#f4f7fb url('https://images.unsplash.com/photo-1578575437130-527eed3abbec?auto=format&fit=crop&w=1920&q=80') center/cover fixed;color:var(--text-hi);font-family:'Heebo',sans-serif;min-height:100vh;padding:28px 32px 40px;}
  body::before{content:'';position:fixed;inset:0;background:rgba(255,255,255,0.90);z-index:-1;}
  .topbar{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:1px solid var(--line);padding-bottom:18px;margin-bottom:20px;flex-wrap:wrap;gap:16px;}
  .brand{display:flex;align-items:center;gap:14px;}
  .brand-mark{width:44px;height:44px;border-radius:8px;background:linear-gradient(155deg,var(--teal),var(--teal-dim));display:flex;align-items:center;justify-content:center;font-family:'Rubik',sans-serif;font-weight:900;font-size:20px;color:#fff;}
  .brand-text .eyebrow{font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:.14em;color:var(--teal);text-transform:uppercase;}
  .brand-text h1{font-family:'Rubik',sans-serif;font-weight:700;font-size:24px;margin-top:2px;}
  .topbar-right{display:flex;gap:28px;align-items:flex-end;}
  .stat-mini{text-align:center;}.stat-mini .n{font-family:'IBM Plex Mono',monospace;font-size:26px;font-weight:600;}
  .stat-mini .l{font-size:11px;color:var(--text-low);margin-top:6px;}
  .clock-block .time{font-family:'IBM Plex Mono',monospace;font-size:30px;font-weight:600;}
  .clock-block .date{font-size:12px;color:var(--text-mid);margin-top:6px;}
  .tabs{display:flex;gap:8px;margin-bottom:20px;border-bottom:1px solid var(--line);}
  .tab{padding:10px 20px;background:transparent;border:none;color:var(--text-mid);font-family:'Heebo',sans-serif;font-weight:500;font-size:15px;cursor:pointer;border-bottom:3px solid transparent;}
  .tab.active{color:var(--teal);border-bottom-color:var(--teal);}
  .panel{display:none;}.panel.active{display:block;}
  .board{display:flex;flex-direction:column;gap:12px;}
  .row{background:var(--bg-panel);border:1px solid var(--line-soft);border-radius:var(--radius);display:grid;grid-template-columns:5px 1.8fr 1.1fr 0.9fr 0.9fr 0.9fr 1.3fr auto;align-items:stretch;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.06);}
  .row .accent{width:5px;}.row.status-ok .accent{background:var(--teal);}.row.status-warn .accent{background:var(--amber);}.row.status-alert .accent{background:var(--red);}.row.status-done .accent{background:var(--blue);}
  .cell{padding:16px 14px;display:flex;flex-direction:column;justify-content:center;border-inline-start:1px solid var(--line-soft);}
  .row .accent + .cell{border-inline-start:none;}
  .label{font-size:11px;color:var(--text-low);letter-spacing:.05em;margin-bottom:6px;}
  input.num-input, select.status-select, input{background:var(--bg-panel-raised);border:1px solid var(--line);border-radius:6px;color:var(--text-hi);font-family:'IBM Plex Mono',monospace;font-size:16px;font-weight:600;padding:6px 8px;width:100%;max-width:120px;text-align:center;}
  select.status-select{font-family:'Heebo',sans-serif;font-size:13px;max-width:100%;text-align:right;}
  .more-cell{align-items:center;justify-content:center;gap:6px;}
  .icon-btn{width:34px;height:34px;border-radius:8px;background:var(--bg-panel-raised);border:1px solid var(--line);color:var(--text-mid);font-size:16px;display:flex;align-items:center;justify-content:center;cursor:pointer;}
  .add-btn{background:var(--teal);color:#fff;border:none;border-radius:6px;padding:8px 16px;font-family:'Heebo',sans-serif;font-weight:600;cursor:pointer;}
  #empty-main{text-align:center;color:var(--text-mid);padding:60px 20px;}
</style>
</head>
<body>
<div class="topbar">
  <div class="brand"><div class="brand-mark">ימ</div><div class="brand-text"><div class="eyebrow">רשות האוכלוסין וההגירה</div><h1>מסך מבצעי — מעבר גבול ימי</h1></div></div>
  <div class="topbar-right">
    <div class="stat-mini"><div class="n" id="stat-ships">0</div><div class="l">אוניות</div></div>
    <div class="stat-mini"><div class="n" id="stat-pax">0</div><div class="l">נוסעים</div></div>
    <div class="clock-block"><div class="time" id="clock">--:--:--</div><div class="date" id="date">--</div></div>
  </div>
</div>
<div class="tabs">
  <button class="tab active" onclick="switchTab('main')">מסך מבצעי</button>
  <button class="tab" onclick="switchTab('forecast')">צפי הגעות</button>
  <button class="tab" onclick="switchTab('archive')">ארכיון</button>
</div>
<div id="panel-main" class="panel active"><div id="board" class="board"></div><div id="empty-main">אין אוניות במסך. הוסף מטאב צפי ההגעות.</div></div>
<div id="panel-forecast" class="panel">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:10px;">
    <h2 style="font-size:16px;color:var(--text-mid);">צפי הגעות</h2>
    <div style="display:flex;gap:8px;">
      <button class="add-btn" onclick="loadForecast()">רענן צפי</button>
      <button class="add-btn" style="background:#4a5568;" onclick="showManualForm()">הוסף אוניה ידנית</button>
    </div>
  </div>
  <p id="forecast-status" style="font-size:13px;color:var(--text-mid);margin-bottom:12px;">לחץ "רענן צפי" או הוסף ידנית</p>
  <div id="manual-form" style="display:none;background:var(--bg-panel);border:1px solid var(--line-soft);border-radius:8px;padding:16px;margin-bottom:16px;">
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:12px;">
      <div><label class="label">שם אוניה</label><input id="m-name" style="width:100%;max-width:none;"></div>
      <div><label class="label">ETA</label><input id="m-eta" placeholder="למשל 22.10 · 14:30" style="width:100%;max-width:none;"></div>
      <div><label class="label">מקור / יעד</label><input id="m-origin" style="width:100%;max-width:none;"></div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:12px;">
      <div><label class="label">רציף</label><input id="m-berth" style="width:100%;max-width:none;"></div>
      <div><label class="label">דגל / מדינה</label><input id="m-flag" style="width:100%;max-width:none;"></div>
      <div><label class="label">IMO</label><input id="m-imo" style="width:100%;max-width:none;"></div>
    </div>
    <button class="add-btn" onclick="addManualShip()">הוסף למסך</button>
    <button class="add-btn" style="background:#718096;margin-inline-start:8px;" onclick="hideManualForm()">ביטול</button>
  </div>
  <div id="forecast-headers" style="display:none;grid-template-columns:2fr 1.2fr 1fr 1fr auto;gap:10px;padding:8px 12px;font-size:11px;color:var(--text-low);font-weight:600;border-bottom:1px solid var(--line);">
    <div>שם אוניה / MMSI</div><div>ETA משוער</div><div>יעד / מקור</div><div>רציף</div><div></div>
  </div>
  <div id="forecast-list"></div>
</div>
<div id="panel-archive" class="panel"><h2 style="font-size:16px;color:var(--text-mid);margin-bottom:16px;">ארכיון</h2><div id="archive-list"></div></div>
<script>
let mainShips=JSON.parse(localStorage.getItem('ashdod_main')||'[]');
let archive=JSON.parse(localStorage.getItem('ashdod_archive')||'[]');
let forecastShips=[];
function esc(s){return String(s||'').replace(/&/g,'&').replace(/</g,'<').replace(/"/g,'"');}
function save(){localStorage.setItem('ashdod_main',JSON.stringify(mainShips));localStorage.setItem('ashdod_archive',JSON.stringify(archive));}
function updateStats(){document.getElementById('stat-ships').textContent=mainShips.length;document.getElementById('stat-pax').textContent=mainShips.reduce((a,s)=>a+(Number(s.pax)||0),0);}
function renderMain(){
  const board=document.getElementById('board'), empty=document.getElementById('empty-main');
  if(mainShips.length===0){board.innerHTML='';empty.style.display='block';return;}
  empty.style.display='none';
  board.innerHTML=mainShips.map(s=>`
    <div class="row status-${s.status||'ok'}">
      <div class="accent"></div>
      <div class="cell ship-cell">
        <div class="flag">${esc(s.flag||'—')} · IMO ${esc(s.imo||'—')}</div>
        <input value="${esc(s.name)}" onchange="updateField(${s.id},'name',this.value)" style="font-weight:700;font-size:18px;border:none;background:transparent;width:100%;">
        <input value="${esc(s.origin||'')}" onchange="updateField(${s.id},'origin',this.value)" style="font-size:12px;border:none;background:transparent;width:100%;margin-top:3px;">
      </div>
      <div class="cell"><div class="label">הגעה</div><input value="${esc(s.eta||'')}" onchange="updateField(${s.id},'eta',this.value)" style="font-family:'IBM Plex Mono',monospace;font-size:15px;border:none;background:transparent;width:100%;"></div>
      <div class="cell"><div class="label">צוות</div><input class="num-input" type="number" min="0" placeholder="—" value="${s.crew??''}" onchange="updateField(${s.id},'crew',this.value)"></div>
      <div class="cell"><div class="label">נוסעים</div><input class="num-input" type="number" min="0" placeholder="—" value="${s.pax??''}" onchange="updateField(${s.id},'pax',this.value)"></div>
      <div class="cell"><div class="label">דורשי טיפול</div><input class="num-input" type="number" min="0" placeholder="—" value="${s.treat??''}" onchange="updateField(${s.id},'treat',this.value)"></div>
      <div class="cell"><div class="label">סטטוס</div>
        <select class="status-select" onchange="updateStatus(${s.id},this.value)">
          <option value="ok" ${s.status==='ok'?'selected':''}>מוכן לביקורת</option>
          <option value="warn" ${s.status==='warn'?'selected':''}>ממתין</option>
          <option value="alert" ${s.status==='alert'?'selected':''}>דורש התייחסות</option>
          <option value="done" ${s.status==='done'?'selected':''}>טופל</option>
        </select>
      </div>
      <div class="cell more-cell"><button class="icon-btn" onclick="removeFromMain(${s.id})">×</button></div>
    </div>`).join('');
}
function updateField(id,field,value){const s=mainShips.find(x=>x.id===id);if(s){if(['crew','pax','treat'].includes(field))value=value===''?null:Number(value);s[field]=value;save();updateStats();}}
function updateStatus(id,status){const s=mainShips.find(x=>x.id===id);if(!s)return;if(status==='done'){archive.push({...s,archivedAt:new Date().toISOString()});mainShips=mainShips.filter(x=>x.id!==id);}else s.status=status;save();renderMain();updateStats();}
function removeFromMain(id){if(!confirm('להסיר?'))return;mainShips=mainShips.filter(s=>s.id!==id);save();renderMain();updateStats();}
function showManualForm(){document.getElementById('manual-form').style.display='block';}
function hideManualForm(){document.getElementById('manual-form').style.display='none';}
function addManualShip(){
  const name=document.getElementById('m-name').value.trim();
  if(!name){alert('יש להזין שם אוניה');return;}
  const ship={id:Date.now(),sourceId:'manual_'+Date.now(),name:name,flag:document.getElementById('m-flag').value.trim(),imo:document.getElementById('m-imo').value.trim(),origin:document.getElementById('m-origin').value.trim()||'—',eta:document.getElementById('m-eta').value.trim()||'—',berth:document.getElementById('m-berth').value.trim(),crew:null,pax:null,treat:null,status:'ok'};
  mainShips.push(ship);save();renderMain();updateStats();hideManualForm();
  ['m-name','m-eta','m-origin','m-berth','m-flag','m-imo'].forEach(id=>document.getElementById(id).value='');
  switchTab('main');
}
async function loadForecast(){
  const status=document.getElementById('forecast-status'), list=document.getElementById('forecast-list'), headers=document.getElementById('forecast-headers');
  status.textContent='טוען...'; list.innerHTML=''; headers.style.display='none';
  try{
    const res=await fetch('/forecast'); if(!res.ok)throw new Error(res.status);
    const data=await res.json();
    forecastShips=(data.ships||[]).map(s=>({id:s.id||('ais_'+s.mmsi),name:s.name||'Unknown',flag:s.flag||'',imo:s.imo||'',origin:s.origin||'—',eta:s.eta||'—',berth:s.berth||'',mmsi:s.mmsi||''}));
    status.textContent=forecastShips.length?`נטענו ${forecastShips.length} אוניות`:'אין אוניות כרגע';
    if(forecastShips.length)headers.style.display='grid';
  }catch(e){status.textContent='שגיאה: '+e.message; forecastShips=[];}
  renderForecast();
}
function renderForecast(){
  const el=document.getElementById('forecast-list'); if(!el)return;
  const already=new Set(mainShips.map(s=>s.sourceId||s.id));
  if(!forecastShips.length){el.innerHTML='<p style="color:var(--text-mid);text-align:center;padding:30px;">אין נתונים</p>';return;}
  el.innerHTML=forecastShips.map(f=>`
    <div style="display:grid;grid-template-columns:2fr 1.2fr 1fr 1fr auto;gap:10px;align-items:center;padding:12px;background:var(--bg-panel);border:1px solid var(--line-soft);border-radius:8px;margin-bottom:8px;">
      <div><input value="${esc(f.name)}" onchange="updateForecastField('${f.id}','name',this.value)" style="font-weight:700;font-size:16px;border:none;background:transparent;width:100%;"><div style="font-size:12px;color:var(--text-mid);">MMSI ${esc(f.mmsi||'—')}</div></div>
      <div><input value="${esc(f.eta||'')}" onchange="updateForecastField('${f.id}','eta',this.value)" style="font-family:'IBM Plex Mono',monospace;border:none;background:transparent;width:100%;"></div>
      <div><input value="${esc(f.origin||'')}" onchange="updateForecastField('${f.id}','origin',this.value)" style="border:none;background:transparent;width:100%;"></div>
      <div><input class="num-input" style="max-width:80px;font-size:13px;" placeholder="רציף" value="${esc(f.berth||'')}" onchange="updateForecastField('${f.id}','berth',this.value)"></div>
      <div>${already.has(f.id)?'<span style="color:var(--text-low);font-size:13px;">כבר במסך</span>':`<button class="add-btn" onclick="addToMain('${f.id}')">הוסף</button>`}</div>
    </div>`).join('');
}
function updateForecastField(id,field,value){const f=forecastShips.find(x=>x.id===id);if(f)f[field]=value;}
function addToMain(fid){const f=forecastShips.find(x=>x.id===fid);if(!f||mainShips.some(s=>s.sourceId===fid))return;mainShips.push({id:Date.now(),sourceId:fid,name:f.name,flag:f.flag,imo:f.imo,origin:f.origin,eta:f.eta,berth:f.berth,crew:null,pax:null,treat:null,status:'ok'});save();renderMain();renderForecast();updateStats();switchTab('main');}
function renderArchive(){const el=document.getElementById('archive-list');if(!el)return;if(!archive.length){el.innerHTML='<p style="color:var(--text-mid);text-align:center;padding:30px;">הארכיון ריק</p>';return;}el.innerHTML=archive.slice().reverse().map(s=>`<div style="background:var(--bg-panel);border:1px solid var(--line-soft);border-radius:8px;padding:14px;margin-bottom:8px;"><strong>${esc(s.name)}</strong> · ${esc(s.eta||'')} · צוות ${s.crew??'—'} · נוסעים ${s.pax??'—'} · דורשי טיפול ${s.treat??'—'}<div style="font-size:12px;color:var(--text-low);margin-top:4px;">נשמר: ${new Date(s.archivedAt).toLocaleString('he-IL')}</div></div>`).join('');}
function switchTab(name){document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));document.querySelector(`.tab[onclick="switchTab('${name}')"]`).classList.add('active');document.getElementById('panel-'+name).classList.add('active');if(name==='archive')renderArchive();if(name==='main')renderMain();}
function tick(){const now=new Date();document.getElementById('clock').textContent=now.toLocaleTimeString('he-IL');document.getElementById('date').textContent=now.toLocaleDateString('he-IL',{weekday:'long',day:'numeric',month:'long'});}
setInterval(tick,1000);tick();renderMain();updateStats();
</script>
</body>
</html>"""

@app.route("/")
def index():
    return HTML

@app.route("/forecast")
def forecast():
    items = list(vessels.values())
    items.sort(key=lambda x: x.get("last_seen", ""), reverse=True)
    return jsonify({
        "updated": datetime.fromtimestamp(last_update, timezone.utc).isoformat() if last_update else None,
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
        print("No API key – serving empty forecast.")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
