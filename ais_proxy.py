#!/usr/bin/env python3
"""Operational board – server-side storage, no AIS required."""
import json, os, threading
from flask import Flask, jsonify, request
from flask_cors import CORS

lock = threading.Lock()
main_ships = []
archive_ships = []

def load_storage():
    global main_ships, archive_ships
    try:
        if os.path.exists("ships.json"):
            with open("ships.json","r",encoding="utf-8") as f:
                data = json.load(f)
                main_ships[:] = data.get("main",[])
                archive_ships[:] = data.get("archive",[])
    except Exception as e:
        print("Load error:", e)

def save_storage():
    with lock:
        with open("ships.json","w",encoding="utf-8") as f:
            json.dump({"main":main_ships,"archive":archive_ships}, f, ensure_ascii=False, indent=2)

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
:root{--bg:#f4f7fb;--panel:#fff;--raised:#f8fafc;--line:#e2e8f0;--text:#1e293b;--mid:#475569;--low:#64748b;--teal:#0d9488;--amber:#d97706;--red:#dc2626;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:#f1f5f9 url('https://images.unsplash.com/photo-1578575437130-527eed3abbec?auto=format&fit=crop&w=1920&q=80') center/cover fixed;color:var(--text);font-family:'Heebo',sans-serif;min-height:100vh;padding:20px;}
body::before{content:'';position:fixed;inset:0;background:rgba(255,255,255,.94);z-index:-1;}
.topbar{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:1px solid var(--line);padding-bottom:14px;margin-bottom:16px;flex-wrap:wrap;gap:12px;}
.brand{display:flex;align-items:center;gap:12px;}
.brand-mark{width:40px;height:40px;border-radius:8px;background:linear-gradient(135deg,var(--teal),#0f766e);display:flex;align-items:center;justify-content:center;font-family:'Rubik',sans-serif;font-weight:700;font-size:18px;color:#fff;}
.brand h1{font-family:'Rubik',sans-serif;font-size:22px;}
.eyebrow{font-size:11px;letter-spacing:.08em;color:var(--teal);}
.stats{display:flex;gap:24px;}
.stat .n{font-family:'IBM Plex Mono',monospace;font-size:24px;font-weight:600;}
.stat .l{font-size:11px;color:var(--low);}
.clock{font-family:'IBM Plex Mono',monospace;font-size:24px;}
.tabs{display:flex;gap:6px;margin-bottom:16px;border-bottom:1px solid var(--line);}
.tab{padding:8px 18px;background:none;border:none;color:var(--mid);font-weight:500;cursor:pointer;border-bottom:3px solid transparent;}
.tab.active{color:var(--teal);border-bottom-color:var(--teal);}
.panel{display:none;}.panel.active{display:block;}
.toolbar{margin-bottom:12px;}
.btn{background:var(--teal);color:#fff;border:none;border-radius:6px;padding:8px 16px;font-weight:600;cursor:pointer;font-family:inherit;}
.btn.gray{background:#64748b;}
.btn.small{padding:6px 10px;font-size:13px;}
table{width:100%;border-collapse:collapse;background:var(--panel);border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.06);}
th,td{padding:10px 8px;text-align:right;border-bottom:1px solid var(--line);vertical-align:top;}
th{background:#f8fafc;font-size:12px;color:var(--low);font-weight:600;white-space:nowrap;}
th input,th select{width:100%;padding:4px 6px;border:1px solid var(--line);border-radius:4px;font-size:12px;background:#fff;margin-top:4px;}
input,select,textarea{width:100%;padding:6px 8px;border:1px solid var(--line);border-radius:6px;font-family:inherit;font-size:14px;background:#fff;}
textarea{min-height:50px;resize:vertical;}
.name-input{font-weight:700;font-size:15px;}
.row-actions{display:flex;gap:6px;flex-direction:column;}
#manual-form{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;margin-bottom:16px;}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:10px;}
#empty{text-align:center;color:var(--mid);padding:40px;background:var(--panel);border-radius:10px;}
.archive-box{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px;margin-bottom:8px;}
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
    <button class="btn" onclick="showManual()">הוסף אוניה</button>
  </div>

  <div id="manual-form" style="display:none;">
    <div class="grid">
      <div><label>שם אוניה *</label><input id="m-name"></div>
      <div><label>סוכן</label><input id="m-agent"></div>
      <div><label>מקור הגעה</label>
        <select id="m-source"><option>חו"ל</option><option>חיפה</option><option>חדרה</option><option>אשקלון</option></select>
      </div>
      <div><label>ETA</label><input type="datetime-local" id="m-eta"></div>
      <div><label>רציף</label><input id="m-berth"></div>
      <div><label>כיוון</label>
        <select id="m-dir"><option value="in">כניסה</option><option value="out">יציאה</option></select>
      </div>
      <div><label>דגל</label><input id="m-flag"></div>
      <div><label>IMO</label><input id="m-imo"></div>
    </div>
    <button class="btn" onclick="addManual()">הוסף</button>
    <button class="btn gray" onclick="hideManual()">ביטול</button>
  </div>

  <div id="table-wrap"></div>
  <div id="empty" style="display:none;">אין אוניות. לחץ "הוסף אוניה".</div>
</div>

<div id="panel-archive" class="panel">
  <h3 style="margin-bottom:8px;color:var(--mid);">כניסות</h3>
  <div id="arch-in"></div>
  <h3 style="margin:16px 0 8px;color:var(--mid);">יציאות</h3>
  <div id="arch-out"></div>
</div>

<script>
let ships = [];
let archive = [];
const STATUS_IN = ['עוגן מחוץ לנמל','מוכן לביקורת','אחרי ביקורת','בטיפול'];
const STATUS_OUT = ['תהליך בדיקת יציאה','אוניה שוחררה'];

function esc(s){return String(s||'').replace(/&/g,'&').replace(/</g,'<').replace(/"/g,'"');}
function fmtEta(iso){if(!iso)return '';try{const d=new Date(iso);return d.toLocaleString('he-IL',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});}catch{return iso;}}

async function load(){
  try{const r=await fetch('/ships');if(r.ok){const d=await r.json();ships=d.main||[];archive=d.archive||[];}}catch(e){}
  render(); updateStats();
}
async function save(){
  try{await fetch('/ships',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({main:ships,archive})});}catch(e){}
}
function updateStats(){
  document.getElementById('stat-ships').textContent=ships.length;
  document.getElementById('stat-pax').textContent=ships.reduce((a,s)=>a+(+s.pax||0),0);
}
function showManual(){document.getElementById('manual-form').style.display='block';}
function hideManual(){document.getElementById('manual-form').style.display='none';}

function addManual(){
  const name=document.getElementById('m-name').value.trim();
  if(!name){alert('יש להזין שם');return;}
  const dir=document.getElementById('m-dir').value;
  ships.push({
    id:Date.now(),
    name,
    agent:document.getElementById('m-agent').value.trim(),
    source:document.getElementById('m-source').value,
    eta:document.getElementById('m-eta').value,
    berth:document.getElementById('m-berth').value.trim(),
    direction:dir,
    flag:document.getElementById('m-flag').value.trim(),
    imo:document.getElementById('m-imo').value.trim(),
    crew:null,pax:null,treat:null,
    notes:'',
    status:dir==='out'?'תהליך בדיקת יציאה':'מוכן לביקורת'
  });
  save();hideManual();
  ['m-name','m-agent','m-eta','m-berth','m-flag','m-imo'].forEach(id=>document.getElementById(id).value='');
  render();updateStats();
}

function getFilters(){
  return {
    name:(document.getElementById('f-name')||{}).value||'',
    agent:(document.getElementById('f-agent')||{}).value||'',
    source:(document.getElementById('f-source')||{}).value||'',
    dir:(document.getElementById('f-dir')||{}).value||'',
    status:(document.getElementById('f-status')||{}).value||''
  };
}

function filtered(){
  const f=getFilters();
  return ships.filter(s=>{
    if(f.name && !s.name.toLowerCase().includes(f.name.toLowerCase())) return false;
    if(f.agent && !(s.agent||'').toLowerCase().includes(f.agent.toLowerCase())) return false;
    if(f.source && s.source!==f.source) return false;
    if(f.dir && s.direction!==f.dir) return false;
    if(f.status && s.status!==f.status) return false;
    return true;
  });
}

function statusOpts(s){
  const list=s.direction==='out'?STATUS_OUT:STATUS_IN;
  return list.map(x=>`<option ${s.status===x?'selected':''}>${x}</option>`).join('');
}

function render(){
  const wrap=document.getElementById('table-wrap');
  const empty=document.getElementById('empty');
  if(!ships.length){wrap.innerHTML='';empty.style.display='block';return;}
  empty.style.display='none';
  const list=filtered();
  wrap.innerHTML=`
  <table>
    <thead>
      <tr>
        <th>שם<br><input id="f-name" placeholder="סינון" oninput="render()"></th>
        <th>סוכן<br><input id="f-agent" placeholder="סינון" oninput="render()"></th>
        <th>מקור<br><select id="f-source" onchange="render()"><option value="">הכל</option><option>חו"ל</option><option>חיפה</option><option>חדרה</option><option>אשקלון</option></select></th>
        <th>ETA</th>
        <th>רציף</th>
        <th>כיוון<br><select id="f-dir" onchange="render()"><option value="">הכל</option><option value="in">כניסה</option><option value="out">יציאה</option></select></th>
        <th>צוות / נוסעים / טיפול</th>
        <th>סטטוס<br><select id="f-status" onchange="render()"><option value="">הכל</option>${[...STATUS_IN,...STATUS_OUT].map(x=>`<option>${x}</option>`).join('')}</select></th>
        <th>הערות</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      ${list.map(s=>`
      <tr>
        <td><input class="name-input" value="${esc(s.name)}" onchange="upd(${s.id},'name',this.value)"><div style="font-size:12px;color:var(--mid);">${esc(s.flag||'')} ${s.imo?'· '+esc(s.imo):''}</div></td>
        <td><input value="${esc(s.agent||'')}" onchange="upd(${s.id},'agent',this.value)"></td>
        <td>
          <select onchange="upd(${s.id},'source',this.value)">
            <option ${s.source==='חו"ל'?'selected':''}>חו"ל</option>
            <option ${s.source==='חיפה'?'selected':''}>חיפה</option>
            <option ${s.source==='חדרה'?'selected':''}>חדרה</option>
            <option ${s.source==='אשקלון'?'selected':''}>אשקלון</option>
          </select>
        </td>
        <td><input type="datetime-local" value="${esc(s.eta||'')}" onchange="upd(${s.id},'eta',this.value)"></td>
        <td><input value="${esc(s.berth||'')}" onchange="upd(${s.id},'berth',this.value)" style="max-width:70px;"></td>
        <td>
          <select onchange="changeDir(${s.id},this.value)">
            <option value="in" ${s.direction==='in'?'selected':''}>כניסה</option>
            <option value="out" ${s.direction==='out'?'selected':''}>יציאה</option>
          </select>
        </td>
        <td>
          <div style="display:flex;gap:4px;">
            <input type="number" placeholder="צוות" value="${s.crew??''}" onchange="upd(${s.id},'crew',this.value)" style="width:60px;">
            <input type="number" placeholder="נוסעים" value="${s.pax??''}" onchange="upd(${s.id},'pax',this.value)" style="width:60px;">
            <input type="number" placeholder="טיפול" value="${s.treat??''}" onchange="upd(${s.id},'treat',this.value)" style="width:60px;">
          </div>
        </td>
        <td><select onchange="changeStatus(${s.id},this.value)">${statusOpts(s)}</select></td>
        <td><textarea onchange="upd(${s.id},'notes',this.value)">${esc(s.notes||'')}</textarea></td>
        <td class="row-actions">
          <button class="btn small" onclick="createExit(${s.id})">צור יציאה</button>
          <button class="btn gray small" onclick="removeShip(${s.id})">×</button>
        </td>
      </tr>`).join('')}
    </tbody>
  </table>`;
  // restore filter values after re-render
  const f=getFilters();
  if(document.getElementById('f-name')) document.getElementById('f-name').value=f.name;
  if(document.getElementById('f-agent')) document.getElementById('f-agent').value=f.agent;
  if(document.getElementById('f-source')) document.getElementById('f-source').value=f.source;
  if(document.getElementById('f-dir')) document.getElementById('f-dir').value=f.dir;
  if(document.getElementById('f-status')) document.getElementById('f-status').value=f.status;
}

function upd(id,field,val){
  const s=ships.find(x=>x.id===id); if(!s)return;
  if(['crew','pax','treat'].includes(field)) val=val===''?null:+val;
  s[field]=val; save(); updateStats();
}
function changeDir(id,dir){
  const s=ships.find(x=>x.id===id); if(!s)return;
  s.direction=dir;
  if(dir==='out' && !STATUS_OUT.includes(s.status)) s.status='תהליך בדיקת יציאה';
  if(dir==='in' && !STATUS_IN.includes(s.status)) s.status='מוכן לביקורת';
  save(); render();
}
function changeStatus(id,status){
  const s=ships.find(x=>x.id===id); if(!s)return;
  if(status==='אוניה שוחררה'){
    archive.push({...s,archivedAt:new Date().toISOString()});
    ships=ships.filter(x=>x.id!==id);
  }else s.status=status;
  save(); render(); renderArchive(); updateStats();
}
function createExit(id){
  const s=ships.find(x=>x.id===id); if(!s)return;
  // archive original
  archive.push({...s,archivedAt:new Date().toISOString()});
  // clone as exit, clear ETA
  const clone={...s,id:Date.now(),direction:'out',status:'תהליך בדיקת יציאה',eta:'',notes:''};
  ships=ships.filter(x=>x.id!==id);
  ships.push(clone);
  save(); render(); renderArchive(); updateStats();
}
function removeShip(id){
  if(!confirm('להסיר?'))return;
  ships=ships.filter(s=>s.id!==id); save(); render(); updateStats();
}
function renderArchive(){
  const renderList=arr=>arr.length?arr.slice().reverse().map(s=>`
    <div class="archive-box">
      <strong>${esc(s.name)}</strong> · סוכן ${esc(s.agent||'—')} · ${esc(s.source||'')} · ${fmtEta(s.eta)} · רציף ${esc(s.berth||'—')}
      <div style="font-size:12px;color:var(--low);margin-top:4px;">צוות ${s.crew??'—'} · נוסעים ${s.pax??'—'} · טיפול ${s.treat??'—'} · ${new Date(s.archivedAt).toLocaleString('he-IL')}</div>
      <textarea style="margin-top:6px;" onchange="editArch(${s.id},this.value)">${esc(s.notes||'')}</textarea>
    </div>`).join(''):'<div style="color:var(--mid);padding:8px;">אין רשומות</div>';
  document.getElementById('arch-in').innerHTML=renderList(archive.filter(s=>s.direction!=='out'));
  document.getElementById('arch-out').innerHTML=renderList(archive.filter(s=>s.direction==='out'));
}
function editArch(id,notes){const s=archive.find(x=>x.id===id);if(s){s.notes=notes;save();}}
function switchTab(name){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.querySelector(`.tab[onclick="switchTab('${name}')"]`).classList.add('active');
  document.getElementById('panel-'+name).classList.add('active');
  if(name==='archive') renderArchive();
}
function tick(){document.getElementById('clock').textContent=new Date().toLocaleTimeString('he-IL',{hour:'2-digit',minute:'2-digit'});}
setInterval(tick,1000);tick();load();
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
    return jsonify({"ok": True, "ships": len(main_ships)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
