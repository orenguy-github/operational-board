#!/usr/bin/env python3
"""Operational board - server-side storage, no AIS required.
Generated from public/board.html by scripts/build-flask.mjs - edit the HTML, then rebuild.
"""
import json, os, threading
from flask import Flask, jsonify, request, Response
from flask_cors import CORS

lock = threading.Lock()
main_ships = []
archive_ships = []


def load_storage():
    try:
        if os.path.exists("ships.json"):
            with open("ships.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                main_ships[:] = data.get("main", [])
                archive_ships[:] = data.get("archive", [])
    except Exception as e:
        print("Load error:", e)


def save_storage():
    with open("ships.json", "w", encoding="utf-8") as f:
        json.dump({"main": main_ships, "archive": archive_ships}, f, ensure_ascii=False, indent=2)


load_storage()
app = Flask(__name__)
CORS(app)

HTML = r"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#060a14">
<title>מסך מבצעי — מעבר גבול ימי</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;600;700;800;900&family=IBM+Plex+Mono:wght@500;600;700&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#060a14;
  --bg-2:#0a1120;
  --panel:rgba(16,25,45,.78);
  --panel-solid:#0e1729;
  --raised:#15203a;
  --line:rgba(120,150,210,.16);
  --line-strong:rgba(120,150,210,.30);
  --text:#eef3ff;
  --mid:#a9b8d8;
  --low:#7d8fb5;

  --cyan:#22d3ee;
  --blue:#60a5fa;
  --green:#34d399;
  --amber:#fbbf24;
  --red:#fb7185;
  --violet:#a78bfa;

  --sans:'Heebo',system-ui,sans-serif;
  --mono:'IBM Plex Mono',ui-monospace,monospace;
}
*{box-sizing:border-box;margin:0;padding:0;}
html{font-size:clamp(13px,.8334vw,44px);}
html,body{height:100%;}
body{
  background:var(--bg);
  color:var(--text);
  font-family:var(--sans);
  overflow:hidden;
  -webkit-font-smoothing:antialiased;
}
body::before{
  content:'';position:fixed;inset:0;z-index:-2;
  background:
    radial-gradient(60rem 36rem at 85% -10%, rgba(34,211,238,.14), transparent 60%),
    radial-gradient(50rem 34rem at -5% 105%, rgba(96,165,250,.12), transparent 60%),
    linear-gradient(180deg,var(--bg-2),var(--bg));
}
body::after{
  content:'';position:fixed;inset:0;z-index:-1;pointer-events:none;
  background-image:
    linear-gradient(var(--line) 1px,transparent 1px),
    linear-gradient(90deg,var(--line) 1px,transparent 1px);
  background-size:3.5rem 3.5rem;
  opacity:.25;
  mask-image:radial-gradient(ellipse at 50% 40%,#000 20%,transparent 75%);
  -webkit-mask-image:radial-gradient(ellipse at 50% 40%,#000 20%,transparent 75%);
}
body.idle.view-display{cursor:none;}

.app{height:100vh;display:flex;flex-direction:column;padding:1.4rem 1.8rem 0;gap:1.1rem;}

/* ---------- Header ---------- */
.header{
  display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:2rem;
}
.brand{display:flex;align-items:center;gap:1rem;}
.brand-mark{
  width:3.6rem;height:3.6rem;border-radius:1rem;display:grid;place-items:center;
  background:linear-gradient(145deg,rgba(34,211,238,.25),rgba(96,165,250,.12));
  border:1px solid rgba(34,211,238,.45);
  box-shadow:0 0 2rem rgba(34,211,238,.25), inset 0 0 1.2rem rgba(34,211,238,.12);
  color:var(--cyan);
}
.brand-mark svg{width:2rem;height:2rem;}
.eyebrow{font-size:.9rem;font-weight:600;letter-spacing:.12em;color:var(--cyan);}
.brand h1{font-size:1.9rem;font-weight:800;line-height:1.15;margin-top:.15rem;letter-spacing:-.01em;}

.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.9rem;max-width:62rem;justify-self:center;width:100%;}
.kpi{
  background:var(--panel);border:1px solid var(--line);border-radius:1rem;
  padding:.8rem 1.2rem;display:flex;flex-direction:column;gap:.1rem;
  backdrop-filter:blur(10px);position:relative;overflow:hidden;
}
.kpi::after{content:'';position:absolute;inset-inline:0;top:0;height:.18rem;background:var(--c,var(--cyan));opacity:.85;}
.kpi .n{font-family:var(--mono);font-weight:700;font-size:2.7rem;line-height:1.05;font-variant-numeric:tabular-nums;}
.kpi .l{font-size:1rem;color:var(--mid);font-weight:500;}
.kpi.k-ships{--c:var(--cyan);}
.kpi.k-crew{--c:var(--blue);}
.kpi.k-pax{--c:var(--violet);}
.kpi.k-treat{--c:var(--green);}
.kpi.k-treat.hot{--c:var(--red);border-color:rgba(251,113,133,.55);background:linear-gradient(180deg,rgba(251,113,133,.16),var(--panel));}
.kpi.k-treat.hot .n{color:var(--red);}
.kpi.k-treat.hot{animation:glow 2.4s ease-in-out infinite;}
@keyframes glow{0%,100%{box-shadow:0 0 0 rgba(251,113,133,0);}50%{box-shadow:0 0 2.2rem rgba(251,113,133,.35);}}

.clock{text-align:end;min-width:13rem;}
.clock .time{font-family:var(--mono);font-weight:600;font-size:3.4rem;line-height:1;letter-spacing:-.02em;font-variant-numeric:tabular-nums;}
.clock .time span{color:var(--cyan);}
.clock .date{font-size:1.1rem;color:var(--mid);margin-top:.4rem;font-weight:500;}

/* ---------- Views ---------- */
.view{display:none;flex:1;min-height:0;}
.view.active{display:flex;flex-direction:column;}
.view-scroll{overflow:auto;padding-bottom:1.2rem;scrollbar-width:thin;scrollbar-color:var(--line-strong) transparent;}

/* ---------- Display (TV) ---------- */
.lanes{flex:1;min-height:0;display:grid;grid-template-columns:1.25fr 1fr;gap:1.4rem;}
.lane{display:flex;flex-direction:column;min-height:0;}
.lane-head{display:flex;align-items:center;gap:.8rem;padding:0 .3rem .8rem;}
.lane-head .ico{width:2.6rem;height:2.6rem;border-radius:.8rem;display:grid;place-items:center;background:color-mix(in srgb,var(--c) 18%,transparent);color:var(--c);border:1px solid color-mix(in srgb,var(--c) 45%,transparent);}
.lane-head .ico svg{width:1.5rem;height:1.5rem;}
.lane-head h2{font-size:1.7rem;font-weight:800;}
.lane-head .count{margin-inline-start:auto;font-family:var(--mono);font-weight:700;font-size:1.5rem;color:var(--c);background:color-mix(in srgb,var(--c) 14%,transparent);padding:.1rem .9rem;border-radius:99px;}
.lane.in{--c:var(--cyan);}
.lane.out{--c:var(--amber);}
.lane-body{flex:1;min-height:0;overflow:hidden;display:flex;flex-direction:column;gap:.65rem;padding-bottom:.3rem;}
.lane-body.overflowing{
  mask-image:linear-gradient(to bottom,#000 calc(100% - 3rem),transparent);
  -webkit-mask-image:linear-gradient(to bottom,#000 calc(100% - 3rem),transparent);
}

.card{
  --c:var(--blue);
  flex:none;position:relative;
  background:linear-gradient(180deg,rgba(24,36,64,.85),var(--panel));
  border:1px solid var(--line);border-radius:1.1rem;
  padding:.75rem 1.2rem;padding-inline-start:1.6rem;
  display:flex;flex-direction:column;gap:.5rem;overflow:hidden;
}
.card::before{
  content:'';position:absolute;inset-block:0;inset-inline-start:0;width:.45rem;background:var(--c);
  box-shadow:0 0 1.4rem var(--c);
}
.card.s-wait{--c:var(--blue);}
.card.s-ready{--c:var(--amber);}
.card.s-ok{--c:var(--green);}
.card.s-active{--c:var(--violet);}
.card.has-treat{border-color:rgba(251,113,133,.45);}

.card-top{display:flex;align-items:center;justify-content:space-between;gap:1rem;}
.ship-name{font-size:1.8rem;font-weight:800;line-height:1.15;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.ship-meta{font-size:1rem;color:var(--mid);margin-top:.2rem;font-weight:500;}
.ship-meta b{color:var(--text);font-weight:600;}
.ship-meta .sep{opacity:.4;margin-inline:.45rem;}

.pill{
  flex:none;display:inline-flex;align-items:center;gap:.6rem;
  padding:.45rem 1.1rem;border-radius:99px;font-weight:700;font-size:1.15rem;white-space:nowrap;
  color:var(--c);background:color-mix(in srgb,var(--c) 15%,transparent);
  border:1px solid color-mix(in srgb,var(--c) 50%,transparent);
}
.pill i{width:.7rem;height:.7rem;border-radius:50%;background:var(--c);box-shadow:0 0 .8rem var(--c);}
.card.s-active .pill i,.card.s-ready .pill i{animation:blink 1.6s ease-in-out infinite;}
@keyframes blink{50%{opacity:.25;}}

.metrics{display:grid;grid-template-columns:1.5fr 1fr .8fr .7fr .8fr .8fr;gap:.6rem;}
.m{display:flex;flex-direction:column;min-width:0;padding-top:.5rem;border-top:1px solid var(--line);}
.m .k{font-size:.9rem;color:var(--low);font-weight:600;letter-spacing:.03em;}
.m .v{font-size:1.6rem;font-weight:700;line-height:1.2;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.m .v.mono{font-family:var(--mono);font-variant-numeric:tabular-nums;}
.m .v.zero{color:var(--low);font-weight:500;}
.m .sub{font-size:.95rem;font-weight:600;color:var(--mid);}
.m .sub.soon{color:var(--amber);}
.m .sub.late{color:var(--red);}
.m.treat .v:not(.zero){color:var(--red);}
.card-notes{font-size:1rem;color:var(--mid);padding:.3rem .8rem;background:rgba(255,255,255,.04);border-radius:.6rem;border:1px dashed var(--line-strong);}

.lane-empty{
  flex:1;display:grid;place-items:center;text-align:center;color:var(--low);font-size:1.4rem;font-weight:500;
  border:1px dashed var(--line-strong);border-radius:1.1rem;min-height:12rem;
}

/* ---------- Footer / nav ---------- */
.footer{
  flex:none;display:flex;align-items:center;justify-content:space-between;gap:1rem;
  padding:.7rem 0 1rem;border-top:1px solid var(--line);color:var(--low);font-size:.95rem;
}
.live{display:flex;align-items:center;gap:.6rem;font-weight:500;}
.live i{width:.65rem;height:.65rem;border-radius:50%;background:var(--green);box-shadow:0 0 .8rem var(--green);animation:blink 2s ease-in-out infinite;}
.live.demo i{background:var(--amber);box-shadow:0 0 .8rem var(--amber);}
.live.err i{background:var(--red);box-shadow:0 0 .8rem var(--red);animation:none;}
.live .demo-tag{color:var(--amber);font-weight:700;}
.nav{display:flex;gap:.3rem;padding:.25rem;background:var(--panel-solid);border:1px solid var(--line);border-radius:.9rem;transition:opacity .5s;}
.nav button{
  background:none;border:none;color:var(--mid);font:600 .95rem var(--sans);padding:.45rem 1.1rem;border-radius:.65rem;cursor:pointer;
}
.nav button:hover{color:var(--text);}
.nav button.active{background:var(--raised);color:var(--cyan);box-shadow:inset 0 0 0 1px rgba(34,211,238,.35);}
.nav .icon-btn{padding:.45rem .7rem;display:grid;place-items:center;}
.nav .icon-btn svg{width:1.1rem;height:1.1rem;}
body.idle.view-display .nav{opacity:0;pointer-events:none;}

/* ---------- Manage ---------- */
.toolbar{display:flex;align-items:center;gap:1rem;margin-bottom:1rem;}
.toolbar h2{font-size:1.4rem;font-weight:800;}
.toolbar .spacer{flex:1;}
.btn{
  background:linear-gradient(180deg,#2dd4ee,#0ea5c6);color:#03111a;border:none;border-radius:.7rem;
  padding:.6rem 1.2rem;font:700 1rem var(--sans);cursor:pointer;
}
.btn:hover{filter:brightness(1.1);}
.btn.ghost{background:var(--raised);color:var(--text);border:1px solid var(--line-strong);}
.btn.danger{background:rgba(251,113,133,.14);color:var(--red);border:1px solid rgba(251,113,133,.4);}
.btn.small{padding:.4rem .75rem;font-size:.9rem;}

#manual-form{background:var(--panel);border:1px solid var(--line-strong);border-radius:1rem;padding:1.2rem;margin-bottom:1rem;backdrop-filter:blur(10px);}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(11rem,1fr));gap:.8rem;margin-bottom:1rem;}
label{display:block;font-size:.85rem;color:var(--mid);font-weight:600;margin-bottom:.3rem;}
input,select,textarea{
  width:100%;padding:.5rem .65rem;border:1px solid var(--line-strong);border-radius:.55rem;
  background:#0a1325;color:var(--text);font:500 .95rem var(--sans);color-scheme:dark;
}
input:focus,select:focus,textarea:focus{outline:2px solid var(--cyan);outline-offset:1px;}
textarea{min-height:3rem;resize:vertical;}
::placeholder{color:var(--low);}

.table-card{background:var(--panel);border:1px solid var(--line);border-radius:1rem;overflow:hidden;}
table{width:100%;border-collapse:collapse;}
th,td{padding:.7rem .6rem;text-align:right;border-bottom:1px solid var(--line);vertical-align:top;}
tbody tr:hover{background:rgba(255,255,255,.025);}
tbody tr:last-child td{border-bottom:none;}
th{background:#0c1528;font-size:.8rem;color:var(--mid);font-weight:700;white-space:nowrap;position:sticky;top:0;z-index:1;}
th input,th select{margin-top:.3rem;padding:.3rem .45rem;font-size:.8rem;}
.name-input{font-weight:800;font-size:1.05rem;}
.cell-sub{font-size:.8rem;color:var(--low);margin-top:.25rem;}
.nums{display:flex;gap:.3rem;}
.nums input{width:4.4rem;text-align:center;font-family:var(--mono);}
.row-actions{display:flex;gap:.4rem;flex-direction:column;min-width:6rem;}
.empty-box{text-align:center;color:var(--mid);padding:3rem;background:var(--panel);border:1px dashed var(--line-strong);border-radius:1rem;font-size:1.1rem;}

/* ---------- Archive ---------- */
.arch-cols{display:grid;grid-template-columns:1fr 1fr;gap:1.2rem;}
.arch-cols h3{font-size:1.2rem;font-weight:800;margin-bottom:.7rem;display:flex;align-items:center;gap:.6rem;}
.arch-cols h3 span{font-family:var(--mono);font-size:.95rem;color:var(--low);}
.archive-box{background:var(--panel);border:1px solid var(--line);border-radius:.9rem;padding:.9rem 1rem;margin-bottom:.6rem;}
.archive-box strong{font-size:1.1rem;}
.archive-box .meta{font-size:.9rem;color:var(--mid);margin-top:.25rem;}
.archive-box .meta2{font-size:.8rem;color:var(--low);margin-top:.25rem;}
.archive-box textarea{margin-top:.5rem;}

@media (max-width:1100px){
  html{font-size:14px;}
  body{overflow:auto;}
  .app{height:auto;min-height:100vh;}
  .header{grid-template-columns:1fr;}
  .kpis{max-width:none;}
  .lanes,.arch-cols{grid-template-columns:1fr;}
  .metrics{grid-template-columns:repeat(3,1fr);}
  .clock{text-align:start;}
}
@media (prefers-reduced-motion:reduce){
  *,*::before{animation:none!important;transition:none!important;}
}
</style>
</head>
<body class="view-display">
<div class="app">

  <header class="header">
    <div class="brand">
      <div class="brand-mark" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v11"/><circle cx="12" cy="5" r="1.6"/><path d="M5 12a7 7 0 0 0 14 0"/><path d="M3 12h4M17 12h4"/><path d="M3 20c1.5 0 1.5-1 3-1s1.5 1 3 1 1.5-1 3-1 1.5 1 3 1 1.5-1 3-1 1.5 1 3 1"/></svg>
      </div>
      <div>
        <div class="eyebrow">רשות האוכלוסין וההגירה</div>
        <h1>מסך מבצעי · מעבר גבול ימי</h1>
      </div>
    </div>

    <div class="kpis" aria-label="סיכום נתונים">
      <div class="kpi k-ships"><div class="n" id="stat-ships">0</div><div class="l">אוניות במסך</div></div>
      <div class="kpi k-crew"><div class="n" id="stat-crew">0</div><div class="l">אנשי צוות</div></div>
      <div class="kpi k-pax"><div class="n" id="stat-pax">0</div><div class="l">נוסעים</div></div>
      <div class="kpi k-treat" id="kpi-treat"><div class="n" id="stat-treat">0</div><div class="l">דורשי טיפול</div></div>
    </div>

    <div class="clock">
      <div class="time" id="clock">--:--<span>:--</span></div>
      <div class="date" id="date">--</div>
    </div>
  </header>

  <!-- Display view (TV) -->
  <main id="view-display" class="view active">
    <div class="lanes">
      <section class="lane in" aria-labelledby="h-in">
        <div class="lane-head">
          <div class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4v14M6 12l6 6 6-6"/></svg></div>
          <h2 id="h-in">כניסות</h2>
          <div class="count" id="count-in">0</div>
        </div>
        <div class="lane-body" id="lane-in"></div>
      </section>
      <section class="lane out" aria-labelledby="h-out">
        <div class="lane-head">
          <div class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20V6M6 12l6-6 6 6"/></svg></div>
          <h2 id="h-out">יציאות</h2>
          <div class="count" id="count-out">0</div>
        </div>
        <div class="lane-body" id="lane-out"></div>
      </section>
    </div>
  </main>

  <!-- Manage view -->
  <section id="view-manage" class="view view-scroll">
    <div class="toolbar">
      <h2>ניהול אוניות</h2>
      <div class="spacer"></div>
      <button class="btn" onclick="showManual()">+ הוסף אוניה</button>
    </div>

    <div id="manual-form" style="display:none;">
      <div class="grid">
        <div><label for="m-name">שם אוניה *</label><input id="m-name"></div>
        <div><label for="m-agent">סוכן</label><input id="m-agent"></div>
        <div><label for="m-source">מקור הגעה</label>
          <select id="m-source"><option>חו"ל</option><option>חיפה</option><option>חדרה</option><option>אשקלון</option></select>
        </div>
        <div><label for="m-eta">ETA</label><input type="datetime-local" id="m-eta"></div>
        <div><label for="m-berth">רציף</label><input id="m-berth"></div>
        <div><label for="m-dir">כיוון</label>
          <select id="m-dir"><option value="in">כניסה</option><option value="out">יציאה</option></select>
        </div>
        <div><label for="m-flag">דגל</label><input id="m-flag"></div>
        <div><label for="m-imo">IMO</label><input id="m-imo"></div>
      </div>
      <div style="display:flex;gap:.6rem;">
        <button class="btn" onclick="addManual()">הוסף</button>
        <button class="btn ghost" onclick="hideManual()">ביטול</button>
      </div>
    </div>

    <div id="table-wrap"></div>
    <div id="empty" class="empty-box" style="display:none;">אין אוניות. לחץ &quot;הוסף אוניה&quot; כדי להתחיל.</div>
  </section>

  <!-- Archive view -->
  <section id="view-archive" class="view view-scroll">
    <div class="arch-cols">
      <div><h3>כניסות <span id="arch-in-count"></span></h3><div id="arch-in"></div></div>
      <div><h3>יציאות <span id="arch-out-count"></span></h3><div id="arch-out"></div></div>
    </div>
  </section>

  <footer class="footer">
    <div class="live" id="live"><i></i><span id="live-text">מתחבר…</span></div>
    <nav class="nav" aria-label="ניווט">
      <button data-view="display" class="active" onclick="switchView('display')">תצוגה</button>
      <button data-view="manage" onclick="switchView('manage')">ניהול</button>
      <button data-view="archive" onclick="switchView('archive')">ארכיון</button>
      <button class="icon-btn" onclick="toggleFullscreen()" title="מסך מלא (F)" aria-label="מסך מלא">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></svg>
      </button>
    </nav>
  </footer>
</div>

<script>
const REFRESH_MS = 10000;
const DEMO_KEY = 'ashdod_board_demo_v2';
const STATUS_IN = ['עוגן מחוץ לנמל','מוכן לביקורת','אחרי ביקורת','בטיפול'];
const STATUS_OUT = ['תהליך בדיקת יציאה','אוניה שוחררה'];
const STATUS_CLASS = {
  'עוגן מחוץ לנמל':'s-wait',
  'מוכן לביקורת':'s-ready',
  'אחרי ביקורת':'s-ok',
  'בטיפול':'s-active',
  'תהליך בדיקת יציאה':'s-ready',
  'אוניה שוחררה':'s-ok'
};

let ships = [];
let archive = [];
let demo = false;
let view = 'display';
let lastUpdate = null;
let loadFailed = false;

function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
const pad = n => String(n).padStart(2,'0');
const num = v => (v===null||v===undefined||v==='') ? null : Number(v);

/* ---------- Data ---------- */
function seedDemo(){
  const at = h => { const d=new Date(Date.now()+h*3600e3); return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`; };
  const base = {notes:'',crew:null,pax:null,treat:null};
  return {
    main:[
      {...base,id:1,name:'MSC Aurora',agent:'ג׳נרל שיפינג',source:'חו"ל',eta:at(1.5),berth:'12',direction:'in',flag:'פנמה',imo:'9839430',crew:24,pax:1480,treat:3,status:'מוכן לביקורת',notes:'נדרש צוות רפואי בעגינה'},
      {...base,id:2,name:'Costa Smeralda',agent:'מרין אקספרס',source:'חיפה',eta:at(-0.4),berth:'7',direction:'in',flag:'איטליה',imo:'9781865',crew:18,pax:920,treat:0,status:'בטיפול'},
      {...base,id:3,name:'Aegean Spirit',agent:'ים תיכון סוכנויות',source:'חו"ל',eta:at(5),berth:'',direction:'in',flag:'יוון',imo:'9456123',crew:16,pax:0,treat:0,status:'עוגן מחוץ לנמל'},
      {...base,id:4,name:'Blue Horizon',agent:'אורבן ים',source:'אשקלון',eta:at(2.2),berth:'4',direction:'in',flag:'קפריסין',imo:'9702221',crew:12,pax:210,treat:1,status:'אחרי ביקורת'},
      {...base,id:5,name:'Mediterranean Pearl',agent:'ג׳נרל שיפינג',source:'חדרה',eta:at(-1.2),berth:'9',direction:'in',flag:'מלטה',imo:'9610458',crew:20,pax:640,treat:0,status:'מוכן לביקורת'},
      {...base,id:6,name:'Nordic Star',agent:'מרין אקספרס',source:'חו"ל',eta:'',berth:'3',direction:'out',flag:'נורווגיה',imo:'9533012',crew:22,pax:310,treat:0,status:'תהליך בדיקת יציאה'},
      {...base,id:7,name:'Sea Voyager',agent:'אורבן ים',source:'חיפה',eta:'',berth:'6',direction:'out',flag:'ליבריה',imo:'9487750',crew:15,pax:0,treat:0,status:'תהליך בדיקת יציאה',notes:'ממתין לאישור סוכן'}
    ],
    archive:[]
  };
}

async function fetchData(){
  try{
    const r = await fetch('/ships',{cache:'no-store'});
    if(!r.ok) throw new Error('http '+r.status);
    const d = await r.json();
    ships = d.main||[]; archive = d.archive||[];
    demo = false; loadFailed = false;
  }catch(e){
    demo = true;
    let d = null;
    try{ d = JSON.parse(localStorage.getItem(DEMO_KEY)||'null'); }catch(_){}
    if(!d){ d = seedDemo(); localStorage.setItem(DEMO_KEY, JSON.stringify(d)); }
    ships = d.main||[]; archive = d.archive||[];
  }
  lastUpdate = new Date();
  setLive();
}

async function save(){
  if(demo){
    try{ localStorage.setItem(DEMO_KEY, JSON.stringify({main:ships,archive})); }catch(_){}
    return;
  }
  try{
    await fetch('/ships',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({main:ships,archive})});
    loadFailed = false;
  }catch(e){ loadFailed = true; }
  setLive();
}

function setLive(){
  const el = document.getElementById('live');
  const t = document.getElementById('live-text');
  el.className = 'live' + (demo ? ' demo' : '') + (loadFailed ? ' err' : '');
  const time = lastUpdate ? lastUpdate.toLocaleTimeString('he-IL') : '';
  t.innerHTML = loadFailed
    ? 'שגיאת שמירה — בדוק חיבור לשרת'
    : (demo ? '<span class="demo-tag">מצב הדגמה</span> · נתונים מקומיים' : `מתעדכן אוטומטית כל ${REFRESH_MS/1000} שניות · עודכן ${time}`);
}

/* ---------- Stats ---------- */
function updateStats(){
  const sum = k => ships.reduce((a,s)=>a+(+s[k]||0),0);
  const treat = sum('treat');
  document.getElementById('stat-ships').textContent = ships.length;
  document.getElementById('stat-crew').textContent = sum('crew').toLocaleString('he-IL');
  document.getElementById('stat-pax').textContent = sum('pax').toLocaleString('he-IL');
  document.getElementById('stat-treat').textContent = treat;
  document.getElementById('kpi-treat').classList.toggle('hot', treat>0);
}

/* ---------- Display ---------- */
function etaInfo(iso){
  if(!iso) return {time:'—',sub:'',cls:''};
  const d = new Date(iso);
  if(isNaN(d)) return {time:esc(iso),sub:'',cls:''};
  const now = new Date();
  const time = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
  const sameDay = d.toDateString()===now.toDateString();
  const dateStr = sameDay ? '' : `${pad(d.getDate())}/${pad(d.getMonth()+1)} `;
  const diff = Math.round((d-now)/60000);
  const abs = Math.abs(diff);
  let rel;
  if(abs>=2880) rel = `${Math.floor(abs/1440)} ימים`;
  else rel = `${Math.floor(abs/60)}:${pad(abs%60)} ש׳`;
  if(diff>=0) return {time:dateStr+time, sub:'בעוד '+rel, cls: diff<30?'soon':''};
  return {time:dateStr+time, sub:'באיחור '+rel, cls:'late'};
}

function metric(k,v,opts={}){
  const zero = (v===null||v===undefined||v===''||v===0);
  const shown = (v===null||v===undefined||v==='') ? '—' : v;
  return `<div class="m ${opts.cls||''}"><span class="k">${k}</span><span class="v ${opts.mono?'mono':''} ${zero&&opts.dimZero?'zero':''}">${esc(shown)}</span></div>`;
}

function card(s){
  const e = etaInfo(s.eta);
  const cls = STATUS_CLASS[s.status] || 's-wait';
  const treat = +s.treat||0;
  return `
  <article class="card ${cls} ${treat>0?'has-treat':''}">
    <div class="card-top">
      <div style="min-width:0;">
        <h3 class="ship-name">${esc(s.name)}</h3>
        <div class="ship-meta">
          ${s.flag?`<b>${esc(s.flag)}</b><span class="sep">·</span>`:''}${s.imo?`IMO ${esc(s.imo)}<span class="sep">·</span>`:''}סוכן: <b>${esc(s.agent||'—')}</b>
        </div>
      </div>
      <span class="pill"><i></i>${esc(s.status)}</span>
    </div>
    <div class="metrics">
      <div class="m"><span class="k">${s.direction==='out'?'יציאה':'הגעה (ETA)'}</span><span class="v mono">${e.time}</span>${e.sub?`<span class="sub ${e.cls}">${e.sub}</span>`:''}</div>
      ${metric('מקור',s.source)}
      ${metric('רציף',s.berth,{mono:true})}
      ${metric('צוות',s.crew,{mono:true,dimZero:true})}
      ${metric('נוסעים',s.pax,{mono:true,dimZero:true})}
      ${metric('טיפול',s.treat,{mono:true,dimZero:true,cls:'treat'})}
    </div>
    ${s.notes?`<div class="card-notes">${esc(s.notes)}</div>`:''}
  </article>`;
}

function sortByEta(a,b){
  const ta = a.eta ? new Date(a.eta).getTime() : Infinity;
  const tb = b.eta ? new Date(b.eta).getTime() : Infinity;
  return (isNaN(ta)?Infinity:ta) - (isNaN(tb)?Infinity:tb);
}

const laneCache = {};
function fillLane(id, list, emptyText){
  const el = document.getElementById(id);
  const html = list.length ? list.map(card).join('') : `<div class="lane-empty">${emptyText}</div>`;
  if(laneCache[id] !== html){
    const top = el.scrollTop;
    el.innerHTML = html;
    el.scrollTop = top;
    laneCache[id] = html;
  }
}

function renderDisplay(){
  const ins = ships.filter(s=>s.direction!=='out').sort(sortByEta);
  const outs = ships.filter(s=>s.direction==='out').sort(sortByEta);
  document.getElementById('count-in').textContent = ins.length;
  document.getElementById('count-out').textContent = outs.length;
  fillLane('lane-in', ins, 'אין כניסות צפויות');
  fillLane('lane-out', outs, 'אין יציאות בתהליך');
}

/* Slow auto-scroll for lanes that overflow the screen */
const scrollState = new WeakMap();
let lastFrame = performance.now();
function autoScroll(now){
  const dt = Math.min(now-lastFrame, 100);
  lastFrame = now;
  if(view==='display'){
    document.querySelectorAll('.lane-body').forEach(el=>{
      const max = el.scrollHeight - el.clientHeight;
      const over = max > 4;
      el.classList.toggle('overflowing', over);
      let st = scrollState.get(el);
      if(!st){ st = {phase:'top',wait:0,pos:0}; scrollState.set(el,st); }
      if(!over){ el.scrollTop = 0; st.phase='top'; st.wait=0; st.pos=0; return; }
      if(st.phase==='top'){ st.wait += dt; if(st.wait>6000){ st.phase='down'; st.wait=0; } }
      else if(st.phase==='down'){
        st.pos += dt*0.035*(parseFloat(getComputedStyle(document.documentElement).fontSize)/16);
        if(st.pos>=max){ st.pos=max; st.phase='bottom'; st.wait=0; }
        el.scrollTop = st.pos;
      } else if(st.phase==='bottom'){
        st.wait += dt;
        if(st.wait>5000){ st.pos=0; el.scrollTop=0; st.phase='top'; st.wait=0; }
      }
    });
  }
  requestAnimationFrame(autoScroll);
}

/* ---------- Manage ---------- */
function showManual(){document.getElementById('manual-form').style.display='block';document.getElementById('m-name').focus();}
function hideManual(){document.getElementById('manual-form').style.display='none';}

function addManual(){
  const name = document.getElementById('m-name').value.trim();
  if(!name){alert('יש להזין שם');return;}
  const dir = document.getElementById('m-dir').value;
  ships.push({
    id:Date.now(), name,
    agent:document.getElementById('m-agent').value.trim(),
    source:document.getElementById('m-source').value,
    eta:document.getElementById('m-eta').value,
    berth:document.getElementById('m-berth').value.trim(),
    direction:dir,
    flag:document.getElementById('m-flag').value.trim(),
    imo:document.getElementById('m-imo').value.trim(),
    crew:null,pax:null,treat:null,notes:'',
    status: dir==='out' ? 'תהליך בדיקת יציאה' : 'מוכן לביקורת'
  });
  save(); hideManual();
  ['m-name','m-agent','m-eta','m-berth','m-flag','m-imo'].forEach(id=>document.getElementById(id).value='');
  renderAll();
}

function getFilters(){
  const v = id => (document.getElementById(id)||{}).value||'';
  return {name:v('f-name'),agent:v('f-agent'),source:v('f-source'),dir:v('f-dir'),status:v('f-status')};
}
function filtered(){
  const f = getFilters();
  return ships.filter(s=>{
    if(f.name && !(s.name||'').toLowerCase().includes(f.name.toLowerCase())) return false;
    if(f.agent && !(s.agent||'').toLowerCase().includes(f.agent.toLowerCase())) return false;
    if(f.source && s.source!==f.source) return false;
    if(f.dir && s.direction!==f.dir) return false;
    if(f.status && s.status!==f.status) return false;
    return true;
  });
}
function statusOpts(s){
  const list = s.direction==='out' ? STATUS_OUT : STATUS_IN;
  return list.map(x=>`<option ${s.status===x?'selected':''}>${x}</option>`).join('');
}
const SOURCES = ['חו"ל','חיפה','חדרה','אשקלון'];

function renderManage(){
  const wrap = document.getElementById('table-wrap');
  const empty = document.getElementById('empty');
  if(!ships.length){wrap.innerHTML='';empty.style.display='block';return;}
  empty.style.display='none';
  const f = getFilters();
  const list = filtered();
  wrap.innerHTML = `
  <div class="table-card"><table>
    <thead><tr>
      <th>שם<br><input id="f-name" placeholder="סינון" oninput="renderManage();refocus('f-name')"></th>
      <th>סוכן<br><input id="f-agent" placeholder="סינון" oninput="renderManage();refocus('f-agent')"></th>
      <th>מקור<br><select id="f-source" onchange="renderManage()"><option value="">הכל</option>${SOURCES.map(x=>`<option>${esc(x)}</option>`).join('')}</select></th>
      <th>ETA</th>
      <th>רציף</th>
      <th>כיוון<br><select id="f-dir" onchange="renderManage()"><option value="">הכל</option><option value="in">כניסה</option><option value="out">יציאה</option></select></th>
      <th>צוות / נוסעים / טיפול</th>
      <th>סטטוס<br><select id="f-status" onchange="renderManage()"><option value="">הכל</option>${[...STATUS_IN,...STATUS_OUT].map(x=>`<option>${x}</option>`).join('')}</select></th>
      <th>הערות</th>
      <th></th>
    </tr></thead>
    <tbody>
    ${list.map(s=>`
      <tr>
        <td><input class="name-input" value="${esc(s.name)}" onchange="upd(${s.id},'name',this.value)"><div class="cell-sub">${esc(s.flag||'')} ${s.imo?'· '+esc(s.imo):''}</div></td>
        <td><input value="${esc(s.agent||'')}" onchange="upd(${s.id},'agent',this.value)"></td>
        <td><select onchange="upd(${s.id},'source',this.value)">${SOURCES.map(x=>`<option ${s.source===x?'selected':''}>${esc(x)}</option>`).join('')}</select></td>
        <td><input type="datetime-local" value="${esc(s.eta||'')}" onchange="upd(${s.id},'eta',this.value)"></td>
        <td><input value="${esc(s.berth||'')}" onchange="upd(${s.id},'berth',this.value)" style="width:4.5rem;"></td>
        <td><select onchange="changeDir(${s.id},this.value)"><option value="in" ${s.direction!=='out'?'selected':''}>כניסה</option><option value="out" ${s.direction==='out'?'selected':''}>יציאה</option></select></td>
        <td><div class="nums">
          <input type="number" min="0" placeholder="צוות" aria-label="צוות" value="${s.crew??''}" onchange="upd(${s.id},'crew',this.value)">
          <input type="number" min="0" placeholder="נוסעים" aria-label="נוסעים" value="${s.pax??''}" onchange="upd(${s.id},'pax',this.value)">
          <input type="number" min="0" placeholder="טיפול" aria-label="דורשי טיפול" value="${s.treat??''}" onchange="upd(${s.id},'treat',this.value)">
        </div></td>
        <td><select onchange="changeStatus(${s.id},this.value)">${statusOpts(s)}</select></td>
        <td><textarea onchange="upd(${s.id},'notes',this.value)">${esc(s.notes||'')}</textarea></td>
        <td class="row-actions">
          <button class="btn small" onclick="createExit(${s.id})">צור יציאה</button>
          <button class="btn danger small" onclick="removeShip(${s.id})">הסר</button>
        </td>
      </tr>`).join('')}
    </tbody>
  </table></div>`;
  ['name','agent','source','dir','status'].forEach(k=>{
    const el = document.getElementById('f-'+k); if(el) el.value = f[k];
  });
}
function refocus(id){const el=document.getElementById(id);if(el){el.focus();const l=el.value.length;el.setSelectionRange(l,l);}}

function upd(id,field,val){
  const s = ships.find(x=>x.id===id); if(!s) return;
  if(['crew','pax','treat'].includes(field)) val = num(val);
  s[field] = val; save(); updateStats();
}
function changeDir(id,dir){
  const s = ships.find(x=>x.id===id); if(!s) return;
  s.direction = dir;
  if(dir==='out' && !STATUS_OUT.includes(s.status)) s.status = 'תהליך בדיקת יציאה';
  if(dir==='in' && !STATUS_IN.includes(s.status)) s.status = 'מוכן לביקורת';
  save(); renderAll();
}
function changeStatus(id,status){
  const s = ships.find(x=>x.id===id); if(!s) return;
  if(status==='אוניה שוחררה'){
    archive.push({...s,status,archivedAt:new Date().toISOString()});
    ships = ships.filter(x=>x.id!==id);
  } else s.status = status;
  save(); renderAll();
}
function createExit(id){
  const s = ships.find(x=>x.id===id); if(!s) return;
  archive.push({...s,archivedAt:new Date().toISOString()});
  const clone = {...s,id:Date.now(),direction:'out',status:'תהליך בדיקת יציאה',eta:'',notes:''};
  ships = ships.filter(x=>x.id!==id);
  ships.push(clone);
  save(); renderAll();
}
function removeShip(id){
  if(!confirm('להסיר את האוניה?')) return;
  ships = ships.filter(s=>s.id!==id); save(); renderAll();
}

/* ---------- Archive ---------- */
function fmtEta(iso){
  if(!iso) return '—';
  const d = new Date(iso);
  return isNaN(d) ? iso : d.toLocaleString('he-IL',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
}
function renderArchive(){
  const list = arr => arr.length ? arr.slice().reverse().map(s=>`
    <div class="archive-box">
      <strong>${esc(s.name)}</strong>
      <div class="meta">סוכן ${esc(s.agent||'—')} · ${esc(s.source||'')} · ${esc(fmtEta(s.eta))} · רציף ${esc(s.berth||'—')}</div>
      <div class="meta2">צוות ${s.crew??'—'} · נוסעים ${s.pax??'—'} · טיפול ${s.treat??'—'} · ${new Date(s.archivedAt).toLocaleString('he-IL')}</div>
      <textarea aria-label="הערות" onchange="editArch(${s.id},this.value)">${esc(s.notes||'')}</textarea>
    </div>`).join('') : '<div class="empty-box" style="padding:1.2rem;">אין רשומות</div>';
  const ins = archive.filter(s=>s.direction!=='out');
  const outs = archive.filter(s=>s.direction==='out');
  document.getElementById('arch-in').innerHTML = list(ins);
  document.getElementById('arch-out').innerHTML = list(outs);
  document.getElementById('arch-in-count').textContent = ins.length;
  document.getElementById('arch-out-count').textContent = outs.length;
}
function editArch(id,notes){const s=archive.find(x=>x.id===id);if(s){s.notes=notes;save();}}

/* ---------- Navigation ---------- */
function renderAll(){
  updateStats();
  if(view==='display') renderDisplay();
  else if(view==='manage') renderManage();
  else renderArchive();
}
function switchView(name){
  if(!['display','manage','archive'].includes(name)) name='display';
  view = name;
  document.querySelectorAll('.view').forEach(p=>p.classList.remove('active'));
  document.getElementById('view-'+name).classList.add('active');
  document.querySelectorAll('.nav [data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===name));
  document.body.classList.remove('view-display','view-manage','view-archive');
  document.body.classList.add('view-'+name);
  if(location.hash.slice(1)!==name) history.replaceState(null,'','#'+name);
  document.body.style.overflow = (name==='display' && innerWidth>1100) ? 'hidden' : '';
  renderAll();
}
function toggleFullscreen(){
  if(document.fullscreenElement) document.exitFullscreen();
  else document.documentElement.requestFullscreen && document.documentElement.requestFullscreen();
}

/* Auto-hide controls and cursor on the TV after a few seconds of inactivity */
let idleTimer;
function wake(){
  document.body.classList.remove('idle');
  clearTimeout(idleTimer);
  idleTimer = setTimeout(()=>document.body.classList.add('idle'), 6000);
}
['mousemove','keydown','touchstart','click'].forEach(ev=>addEventListener(ev,wake,{passive:true}));
addEventListener('keydown',e=>{
  if(/INPUT|TEXTAREA|SELECT/.test((e.target||{}).tagName)) return;
  if(e.key==='f'||e.key==='F') toggleFullscreen();
  if(e.key==='1') switchView('display');
  if(e.key==='2') switchView('manage');
  if(e.key==='3') switchView('archive');
});
addEventListener('hashchange',()=>switchView(location.hash.slice(1)));

/* ---------- Clock ---------- */
function tick(){
  const now = new Date();
  document.getElementById('clock').innerHTML = `${pad(now.getHours())}:${pad(now.getMinutes())}<span>:${pad(now.getSeconds())}</span>`;
  document.getElementById('date').textContent = now.toLocaleDateString('he-IL',{weekday:'long',day:'numeric',month:'long',year:'numeric'});
}
setInterval(tick,1000); tick();

/* ---------- Refresh loop ---------- */
function userIsEditing(){
  if(document.getElementById('manual-form').style.display==='block') return true;
  const a = document.activeElement;
  return !!a && /INPUT|TEXTAREA|SELECT/.test(a.tagName) && a.closest('#view-manage,#view-archive');
}
async function refresh(){
  if(!demo && userIsEditing()) return;
  await fetchData();
  renderAll();
}
setInterval(refresh, REFRESH_MS);
setInterval(()=>{ if(view==='display') renderDisplay(); }, 30000);

(async function init(){
  await fetchData();
  switchView(location.hash.slice(1) || 'display');
  wake();
  requestAnimationFrame(autoScroll);
})();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return Response(HTML, mimetype="text/html")


@app.route("/ships", methods=["GET"])
def get_ships():
    resp = jsonify({"main": main_ships, "archive": archive_ships})
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/ships", methods=["POST"])
def save_ships():
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
