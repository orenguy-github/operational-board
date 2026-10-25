#!/usr/bin/env python3
"""Operational board with server-side storage. AIS optional."""
import asyncio, json, os, time, threading
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS

API_KEY = os.environ.get("AISSTREAM_API_KEY", "")
vessels = {}
last_update = 0
lock = threading.Lock()
main_ships = []
archive_ships = []

def load_storage():
    global main_ships, archive_ships
    try:
        if os.path.exists("ships.json"):
            with open("ships.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                main_ships[:] = data.get("main", [])
                archive_ships[:] = data.get("archive", [])
    except Exception as e:
        print("Load storage error:", e)

def save_storage():
    with lock:
        with open("ships.json", "w", encoding="utf-8") as f:
            json.dump({"main": main_ships, "archive": archive_ships}, f, ensure_ascii=False, indent=2)

load_storage()

app = Flask(__name__)
CORS(app)

HTML = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>מסך מבצעי — מעבר גבול ימי</title>
<link href="https://fonts.googleapis.com/css2?family=Rubik:wght@500;700&family=Heebo:wght@400;500;600&family=IBM+Plex+Mono:wght@500&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#f4f7fb;--panel:#fff;--raised:#f0f4f8;--line:#d0d7e2;--soft:#e2e8f0;
  --text:#1a2332;--mid:#4a5568;--low:#718096;--teal:#0d9488;--amber:#d97706;--red:#dc2626;--blue:#2563eb;
}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:#f4f7fb url('https://images.unsplash.com/photo-1578575437130-527eed3abbec?auto=format&fit=crop&w=1920&q=80') center/cover fixed;color:var(--text);font-family:'Heebo',sans-serif;min-height:100vh;padding:20px 24px 40px;}
body::before{content:'';position:fixed;inset:0;background:rgba(255,255,255,.92);z-index:-1;}
.topbar{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:1px solid var(--line);padding-bottom:14px;margin-bottom:16px;flex-wrap:wrap;gap:12px;}
.brand{display:flex;align-items:center;gap:12px;}
.brand-mark{width:40px;height:40px;border-radius:8px;background:linear-gradient(155deg,var(--teal),#0f766e);display:flex;align-items:center;justify-content:center;font-family:'Rubik',sans-serif;font-weight:700;font-size:18px;color:#fff;}
.brand h1{font-family:'Rubik',sans-serif;font-size:22px;}
.eyebrow{font-size:11px;letter-spacing:.1em;color:var(--teal);font-family:'IBM Plex Mono',monospace;}
.stats{display:flex;gap:24px;}
.stat .n{font-family:'IBM Plex Mono',monospace;font-size:24px;font-weight:600;}
.stat .l{font-size:11px;color:var(--low);}
.clock{font-family:'IBM Plex Mono',monospace;font-size:26px;}
.tabs{display:flex;gap:6px;margin-bottom:16px;border-bottom:1px solid var(--line);}
.tab{padding:8px 18px;background:none;border:none;color:var(--mid);font-weight:500;cursor:pointer;border-bottom:3px solid transparent;}
.tab.active{color:var(--teal);border-bottom-color:var(--teal);}
.panel{display:none;}.panel.active{display:block;}
.toolbar{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap;align-items:center;}
.btn{background:var(--teal);color:#fff;border:none;border-radius:6px;padding:8px 14px;font-weight:600;cursor:pointer;font-family:inherit;}
.btn.gray{background:#4a5568;}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;font-size:13px;}
.filters input,.filters select{padding:6px 8px;border:1px solid var(--line);border-radius:6px;background:var(--raised);font-family:inherit;}
.board{display:flex;flex-direction:column;gap:10px;}
.row{background:var(--panel);border:1px solid var(--soft);border-radius:10px;display:grid;grid-template-columns:5px 1.6fr 1fr 0.8fr 0.8fr 0.8fr 1.1fr 0.9fr auto;align-items:stretch;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.05);}
.accent{width:5px;}
.row.ok .accent{background:var(--teal);} .row.warn .accent{background:var(--amber);} .row.alert .accent{background:var(--red);} .row.done .accent{background:var(--blue);}
.cell{padding:12px 10px;display:flex;flex-direction:column;justify-content:center;border-inline-start:1px solid var(--soft);}
.row .accent+.cell{border-inline-start:none;}
.label{font-size:10px;color:var(--low);margin-bottom:4px;}
input,select,textarea{background:var(--raised);border:1px solid var(--line);border-radius:6px;padding:5px 7px;font-family:inherit;font-size:14px;width:100%;}
input.name{font-weight:700;font-size:16px;border:none;background:transparent;}
.notes-wrap{margin-top:6px;}
.notes-toggle{font-size:12px;color:var(--teal);cursor:pointer;background:none;border:none;padding:0;}
textarea.notes{min-height:60px;resize:vertical;margin-top:4px;display:none;}
.more{align-items:center;justify-content:center;}
.icon-btn{width:32px;height:32px;border-radius:6px;border:1px solid var(--line);background:var(--raised);cursor:pointer;}
#manual-form,#empty{background:var(--panel);border:1px solid var(--soft);border-radius:10px;padding:16px;margin-bottom:12px;}
#empty{text-align:center;color:var(--mid);padding:40px;}
.grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-bottom:10px;}
.archive-section{margin-bottom:20px;}
.archive-section h3{font-size:15px;margin-bottom:8px;color:var(--mid);}
</style>
</head>
<body>
<div class="topbar">
  <div class="brand">
    <div class="brand-mark">ימ</div>
    <div>
      <div class="eyebrow">רשות האוכלוסין וההגירה</div>
      <h1>מסך מבצעי — מעבר גבול ימי</h1>
    </div>
  </div>
  <div class="stats">
    <div class="stat"><div class="n" id="stat-ships">0</div><div class="l">אוניות</div></div>
    <div class="stat"><div class="n" id="stat-pax">0</div><div class="l">נוסעים</div></div>
  </div>
  <div class="clock" id="clock">--:--</div>
</div>

<div class="tabs">
  <button class="tab active" onclick="switchTab('main')">מסך מבצעי</button>
  <button class="tab" onclick="switchTab('archive')">ארכיון</button>
</div>

<div id="panel-main" class="panel active">
  <div class="toolbar">
    <button class="btn" onclick="showManual()">הוסף אוניה ידנית</button>
  </div>
  <div id="manual-form" style="display:none;">
    <div class="grid3">
      <div><label class="label">שם אוניה *</label><input id="m-name"></div>
      <div><label class="label">מקור הגעה</label>
        <select id="m-source"><option>חו"ל</option><option>חיפה</option><option>חדרה</option><option>אשקלון</option></select>
      </div>
      <div><label class="label">ETA</label><input id="m-eta" placeholder="22.10 · 14:30"></div>
      <div><label class="label">רציף</label><input id="m-berth"></div>
      <div><label class="label">כיוון</label>
        <select id="m-dir"><option value="in">כניסה</option><option value="out">יציאה</option></select>
      </div>
      <div><label class="label">דגל</label><input id="m-flag"></div>
      <div><label class="label">IMO</label><input id="m-imo"></div>
    </div>
    <button class="btn" onclick="addManual()">הוסף למסך</button>
    <button class="btn gray" onclick="hideManual()">ביטול</button>
  </div>

  <div class="filters">
    <input id="f-name" placeholder="סינון שם..." oninput="renderMain()">
    <select id="f-dir" onchange="renderMain()"><option value="">כל הכיוונים</option><option value="in">כניסה</option><option value="out">יציאה</option></select>
    <select id="f-status" onchange="renderMain()"><option value="">כל הסטטוסים</option></select>
    <select id="f-source" onchange="renderMain()"><option value="">כל המקורות</option><option>חו"ל</option><option>חיפה</option><option>חדרה</option><option>אשקלון</option></select>
    <button class="btn gray" onclick="clearFilters()">נקה סינון</button>
  </div>

  <div id="board" class="board"></div>
  <div id="empty">אין אוניות במסך. לחץ "הוסף אוניה ידנית".</div>
</div>

<div id="panel-archive" class="panel">
  <div class="archive-section">
    <h3>כניסות</h3>
    <div id="arch-in"></div>
  </div>
  <div class="archive-section">
    <h3>יציאות</h3>
    <div id="arch-out"></div>
  </div>
</div>

<script>
let ships = [];
let archive = [];
const STATUS_IN = ['עוגן מחוץ לנמל','מוכן לביקורת','אחרי ביקורת','בטיפול'];
const STATUS_OUT = ['תהליך בדיקת יציאה','אוניה שוחררה'];

function esc(s){return String(s||'').replace(/&/g,'&').replace(/</g,'<').replace(/"/g,'"');}

async function load(){
  try{
    const r = await fetch('/ships');
    if(r.ok){const d=await r.json(); ships=d.main||[]; archive=d.archive||[];}
  }catch(e){}
  renderMain(); renderArchive(); updateStats();
}
async function save(){
  try{await fetch('/ships',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({main:ships,archive})});}catch(e){}
}

function updateStats(){
  document.getElementById('stat-ships').textContent = ships.length;
  document.getElementById('stat-pax').textContent = ships.reduce((a,s)=>a+(Number(s.pax)||0),0);
}

function showManual(){document.getElementById('manual-form').style.display='block';}
function hideManual(){document.getElementById('manual-form').style.display='none';}

function addManual(){
  const name = document.getElementById('m-name').value.trim();
  if(!name){alert('יש להזין שם');return;}
  const dir = document.getElementById('m-dir').value;
  ships.push({
    id: Date.now(),
    name,
    source: document.getElementById('m-source').value,
    eta: document.getElementById('m-eta').value.trim(),
    berth: document.getElementById('m-berth').value.trim(),
    direction: dir,
    flag: document.getElementById('m-flag').value.trim(),
    imo: document.getElementById('m-imo').value.trim(),
    crew: null, pax: null, treat: null,
    notes: '',
    status: dir==='out' ? 'תהליך בדיקת יציאה' : 'מוכן לביקורת',
    notesOpen: false
  });
  save(); hideManual();
  ['m-name','m-eta','m-berth','m-flag','m-imo'].forEach(id=>document.getElementById(id).value='');
  renderMain(); updateStats();
}

function clearFilters(){
  document.getElementById('f-name').value='';
  document.getElementById('f-dir').value='';
  document.getElementById('f-status').value='';
  document.getElementById('f-source').value='';
  renderMain();
}

function filtered(){
  const n=document.getElementById('f-name').value.toLowerCase();
  const d=document.getElementById('f-dir').value;
  const st=document.getElementById('f-status').value;
  const src=document.getElementById('f-source').value;
  return ships.filter(s=>{
    if(n && !s.name.toLowerCase().includes(n)) return false;
    if(d && s.direction!==d) return false;
    if(st && s.status!==st) return false;
    if(src && s.source!==src) return false;
    return true;
  });
}

function statusOptions(s){
  const list = s.direction==='out' ? STATUS_OUT : STATUS_IN;
  return list.map(x=>`<option value="${x}" ${s.status===x?'selected':''}>${x}</option>`).join('');
}

function renderMain(){
  const board=document.getElementById('board'), empty=document.getElementById('empty');
  const list = filtered();
  if(ships.length===0){board.innerHTML='';empty.style.display='block';return;}
  empty.style.display='none';
  board.innerHTML = list.map(s=>`
    <div class="row ${s.status.includes('שוחררה')?'done':s.status.includes('בטיפול')||s.status.includes('עוגן')?'warn':'ok'}">
      <div class="accent"></div>
      <div class="cell">
        <input class="name" value="${esc(s.name)}" onchange="upd(${s.id},'name',this.value)">
        <div style="font-size:12px;color:var(--mid);margin-top:2px;">${esc(s.flag||'')} ${s.imo?'· IMO '+esc(s.imo):''}</div>
        <div class="notes-wrap">
          <button class="notes-toggle" onclick="toggleNotes(${s.id})">${s.notesOpen?'הסתר הערות':'הערות'}</button>
          <textarea class="notes" id="notes-${s.id}" style="${s.notesOpen?'display:block;':''}" onchange="upd(${s.id},'notes',this.value)">${esc(s.notes||'')}</textarea>
        </div>
      </div>
      <div class="cell">
        <div class="label">מקור הגעה</div>
        <select onchange="upd(${s.id},'source',this.value)">
          <option ${s.source==='חו"ל'?'selected':''}>חו"ל</option>
          <option ${s.source==='חיפה'?'selected':''}>חיפה</option>
          <option ${s.source==='חדרה'?'selected':''}>חדרה</option>
          <option ${s.source==='אשקלון'?'selected':''}>אשקלון</option>
        </select>
      </div>
      <div class="cell">
        <div class="label">ETA</div>
        <input value="${esc(s.eta||'')}" onchange="upd(${s.id},'eta',this.value)">
      </div>
      <div class="cell">
        <div class="label">רציף</div>
        <input value="${esc(s.berth||'')}" onchange="upd(${s.id},'berth',this.value)">
      </div>
      <div class="cell">
        <div class="label">כיוון</div>
        <select onchange="changeDir(${s.id},this.value)">
          <option value="in" ${s.direction==='in'?'selected':''}>כניסה</option>
          <option value="out" ${s.direction==='out'?'selected':''}>יציאה</option>
        </select>
      </div>
      <div class="cell">
        <div class="label">צוות / נוסעים / דורשי טיפול</div>
        <div style="display:flex;gap:4px;">
          <input type="number" placeholder="צוות" value="${s.crew??''}" onchange="upd(${s.id},'crew',this.value)" style="max-width:60px;">
          <input type="number" placeholder="נוסעים" value="${s.pax??''}" onchange="upd(${s.id},'pax',this.value)" style="max-width:60px;">
          <input type="number" placeholder="טיפול" value="${s.treat??''}" onchange="upd(${s.id},'treat',this.value)" style="max-width:60px;">
        </div>
      </div>
      <div class="cell">
        <div class="label">סטטוס</div>
        <select onchange="changeStatus(${s.id},this.value)">${statusOptions(s)}</select>
      </div>
      <div class="cell more"><button class="icon-btn" onclick="removeShip(${s.id})">×</button></div>
    </div>
  `).join('') || '<div style="text-align:center;color:var(--mid);padding:20px;">אין תוצאות לסינון</div>';
}

function toggleNotes(id){
  const s=ships.find(x=>x.id===id); if(!s)return;
  s.notesOpen = !s.notesOpen;
  renderMain();
}

function upd(id,field,val){
  const s=ships.find(x=>x.id===id); if(!s)return;
  if(['crew','pax','treat'].includes(field)) val = val===''?null:Number(val);
  s[field]=val;
  save(); updateStats();
}

function changeDir(id,dir){
  const s=ships.find(x=>x.id===id); if(!s)return;
  s.direction=dir;
  if(dir==='out' && !STATUS_OUT.includes(s.status)) s.status='תהליך בדיקת יציאה';
  if(dir==='in' && !STATUS_IN.includes(s.status)) s.status='מוכן לביקורת';
  save(); renderMain();
}

function changeStatus(id,status){
  const s=ships.find(x=>x.id===id); if(!s)return;
  if(status==='אוניה שוחררה'){
    archive.push({...s, archivedAt:new Date().toISOString(), finalStatus:status});
    ships=ships.filter(x=>x.id!==id);
  }else{
    s.status=status;
  }
  save(); renderMain(); renderArchive(); updateStats();
}

function removeShip(id){
  if(!confirm('להסיר את האוניה?'))return;
  ships=ships.filter(s=>s.id!==id);
  save(); renderMain(); updateStats();
}

function renderArchive(){
  const inn=document.getElementById('arch-in'), out=document.getElementById('arch-out');
  const renderList = arr => arr.length ? arr.slice().reverse().map(s=>`
    <div style="background:var(--panel);border:1px solid var(--soft);border-radius:8px;padding:12px;margin-bottom:8px;">
      <strong>${esc(s.name)}</strong> · ${esc(s.source||'')} · ${esc(s.eta||'')} · רציף ${esc(s.berth||'—')}
      <div style="font-size:12px;color:var(--low);margin-top:4px;">
        צוות ${s.crew??'—'} · נוסעים ${s.pax??'—'} · דורשי טיפול ${s.treat??'—'} · נשמר ${new Date(s.archivedAt).toLocaleString('he-IL')}
      </div>
      <textarea style="width:100%;margin-top:6px;min-height:40px;" onchange="editArchive(${s.id},this.value)">${esc(s.notes||'')}</textarea>
    </div>
  `).join('') : '<div style="color:var(--mid);padding:10px;">אין רשומות</div>';

  inn.innerHTML = renderList(archive.filter(s=>s.direction!=='out'));
  out.innerHTML = renderList(archive.filter(s=>s.direction==='out'));
}

function editArchive(id, notes){
  const s=archive.find(x=>x.id===id); if(s){s.notes=notes; save();}
}

function switchTab(name){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.querySelector(`.tab[onclick="switchTab('${name}')"]`).classList.add('active');
  document.getElementById('panel-'+name).classList.add('active');
  if(name==='archive') renderArchive();
}

function tick(){document.getElementById('clock').textContent=new Date().toLocaleTimeString('he-IL',{hour:'2-digit',minute:'2-digit'});}
setInterval(tick,1000); tick();
load();
</script>
</body>
</html>"""

@app.route("/")
def index():
    return HTML

@app.route("/ships", methods=["GET"])
def get_ships():
    return jsonify({"main": main_ships, "archive": archive_ships})

@app.route("/ships", methods=["POST"])
def save_ships():
    global main_ships, archive_ships
    data = request.get_json(force=True) or {}
    with lock:
        main_ships[:] = data.get("main", [])
        archive_ships[:] = data.get("archive", [])
        save_storage()
    return jsonify({"ok": True})

@app.route("/health")
def health():
    return jsonify({"ok": True, "ships": len(main_ships), "archive": len(archive_ships)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
