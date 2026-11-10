import base64
import csv
import io
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

APP_DIR = Path(__file__).parent
ASSETS = APP_DIR / "assets"
DB_PATH = APP_DIR / "telethon.db"
DEFAULT_GOAL = 500

st.set_page_config(page_title="1 € = 1 kilomètre | Les Vieux Volants du Vimeu",
                   page_icon="🚐", layout="wide", initial_sidebar_state="collapsed")

PAPER, GREEN, RUST, INK, GOLD = "#F3EAD8", "#203B32", "#A94F3D", "#292B25", "#D8AE62"

st.markdown(f"""
<style>
.stApp {{ background:{PAPER}; color:{INK}; }}
.block-container {{ max-width:100%; padding:.6rem 1.2rem 0; }}
div[data-testid=stVerticalBlock] {{ gap:.6rem; }}
.top {{ display:flex; align-items:center; gap:1rem; background:{GREEN}; border:2px solid {GOLD}; border-radius:16px; padding:.4rem 1rem; }}
.top .logo {{ background:#FBF7ED; border-radius:12px; padding:4px 8px; height:78px; display:flex; align-items:center; }}
.top .logo img {{ max-height:70px; max-width:220px; width:auto; }}
.top .t {{ flex:1; text-align:center; color:#FFF8E9; }}
.top h1 {{ font-family:Georgia,serif; font-size:clamp(1.5rem,3.2vw,2.8rem); margin:0; line-height:1.1; }}
.top p {{ margin:.2rem 0 0; color:#E8D9B9; font-size:clamp(.8rem,1.3vw,1.1rem); }}
.bar {{ height:14px; background:#3B574C; border-radius:8px; overflow:hidden; margin-top:.35rem; }}
.bar i {{ display:block; height:100%; background:{GOLD}; }}
#MainMenu, footer, header {{ visibility:hidden; }}
.hero {{ background:{GREEN}; color:#FFF8E9; padding:1rem 1.4rem; border:2px solid {GOLD};
  border-radius:16px; text-align:center; }}
.hero h1 {{ font-family:Georgia,serif; font-size:clamp(1.8rem,4vw,3.2rem); margin:0; }}
.hero p {{ margin:.25rem 0 0; color:#E8D9B9; font-size:1.05rem; }}
.metric {{ background:{GREEN}; color:#FFF8E9; border:1px solid {GOLD}; border-radius:14px;
  padding:.45rem 1.1rem; height:100px; }}
.metric small {{ color:#E8D9B9; font-size:.95rem; }}
.metric strong {{ display:block; font-size:clamp(1.5rem,2.6vw,2.3rem); line-height:1.15; }}
.panel {{ background:#FBF7ED; border:1px solid #D7CBB4; border-radius:14px; padding:1rem 1.2rem; }}
div.stButton > button, div.stFormSubmitButton > button {{ background:{GREEN}; color:#FFF8E9;
  border:0; border-radius:10px; font-weight:700; min-height:3rem; font-size:1.05rem; }}
div.stButton > button:hover, div.stFormSubmitButton > button:hover {{ background:{RUST}; color:#fff; }}
.stProgress > div > div > div > div {{ background-color:{RUST}; }}
</style>""", unsafe_allow_html=True)

# ---------- Base de données ----------
@st.cache_resource
def get_db():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.execute("""CREATE TABLE IF NOT EXISTS donations (
        id INTEGER PRIMARY KEY AUTOINCREMENT, km INTEGER NOT NULL,
        note TEXT, created_at TEXT NOT NULL)""")
    con.commit()
    return con

db = get_db()

def total_km():
    return int(db.execute("SELECT COALESCE(SUM(km),0) FROM donations").fetchone()[0])

def recent(limit=8):
    return db.execute("SELECT km, note, created_at FROM donations ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

def add_donation(km, note):
    db.execute("INSERT INTO donations(km,note,created_at) VALUES (?,?,?)",
               (int(km), (note or "").strip(), datetime.now().strftime("%d/%m/%Y %H:%M")))
    db.commit()

def undo_last():
    db.execute("DELETE FROM donations WHERE id=(SELECT MAX(id) FROM donations)")
    db.commit()

def export_csv():
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["km", "note", "date"])
    w.writerows(db.execute("SELECT km, note, created_at FROM donations ORDER BY id").fetchall())
    return buf.getvalue().encode("utf-8-sig")

# ---------- Configuration ----------
try:
    goal = max(int(st.secrets.get("OBJECTIF_KM", DEFAULT_GOAL)), 1)
except Exception:
    goal = DEFAULT_GOAL
try:
    admin_password = st.secrets["ADMIN_PASSWORD"]
except Exception:
    admin_password = os.environ.get("ADMIN_PASSWORD", "")
mode = st.query_params.get("mode", "public")

def fmt(n):
    return f"{n:,}".replace(",", " ")

# ---------- Carte animée ----------
# Coordonnées dans l'image assets/carte_vimeu.png (705 x 470 px), nom = étape
ROUTE = [
    (130, 315, "Feuquières-en-Vimeu"), (140, 275, None), (175, 210, None),
    (205, 155, "Woincourt"), (240, 125, None), (303, 118, "Friville-Escarbotin"),
    (360, 98, None), (400, 115, None), (433, 146, "Fressenneville"),
    (445, 185, None), (485, 205, None), (525, 236, "Tully"),
    (545, 285, None), (563, 341, "Aigneville"),
]

def build_map(prev_total, total):
    img = base64.b64encode((ASSETS / "carte_vimeu.png").read_bytes()).decode()
    cum, acc = [0.0], 0.0
    for a, b in zip(ROUTE, ROUTE[1:]):
        acc += ((b[0]-a[0])**2 + (b[1]-a[1])**2) ** 0.5
        cum.append(acc)
    stops = [(x, y, n, cum[i] / acc) for i, (x, y, n) in enumerate(ROUTE) if n]
    d = "M" + " L".join(f"{x} {y}" for x, y, _ in ROUTE)
    stops_js = "[" + ",".join(f'{{x:{x},y:{y},f:{f:.4f}}}' for x, y, _, f in stops) + "]"
    car_file = ASSETS / "voiture.png"
    if car_file.exists():
        cimg = base64.b64encode(car_file.read_bytes()).decode()
        car_svg = f'<image href="data:image/png;base64,{cimg}" x="-28" y="-14.3" width="56" height="28.6"/>'
    else:
        car_svg = f'<rect x="-18" y="-6" width="36" height="14" rx="5" fill="#F2C34E" stroke="{GREEN}" stroke-width="2"/>'
    p0, p1 = min(prev_total / goal, 1), min(total / goal, 1)
    return f"""
<style>html,body{{margin:0;overflow:hidden}}</style>
<div id="wrap" style="display:flex;justify-content:center;align-items:center;width:100%;height:100%">
<div id="box" style="position:relative;border-radius:14px;overflow:hidden;border:2px solid {GOLD};background:{PAPER}">
 <img src="data:image/png;base64,{img}" style="display:block;width:100%;height:100%">
 <svg id="s" viewBox="0 0 705 470" style="position:absolute;inset:0;width:100%;height:100%">
  <path id="r" d="{d}" fill="none" stroke="{GREEN}" stroke-width="4" stroke-dasharray="2 9" stroke-linecap="round" opacity=".5"/>
  <path id="done" d="{d}" fill="none" stroke="{RUST}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
  <g id="checks"></g>
  <g id="car"><circle r="34" fill="#FFF8E9" stroke="{RUST}" stroke-width="4"/>
   {car_svg}</g>
 </svg>
</div></div>
<script>
function fit(){{
  try{{window.frameElement.style.height=Math.max(380,window.parent.innerHeight-300)+'px';}}catch(e){{}}
  const W=window.innerWidth,H=window.innerHeight,k=Math.min(W/705,H/470),b=document.getElementById('box');
  b.style.width=(705*k-4)+'px';b.style.height=(470*k-4)+'px';
}}
fit();window.addEventListener('resize',fit);
try{{window.parent.addEventListener('resize',fit);}}catch(e){{}}
const path=document.getElementById('r'), done=document.getElementById('done'),
      car=document.getElementById('car'), checks=document.getElementById('checks');
const L=path.getTotalLength(), stops={stops_js}, p0={p0}, p1={p1};
done.style.strokeDasharray=L;
stops.forEach(s=>{{const c=document.createElementNS('http://www.w3.org/2000/svg','text');
  c.setAttribute('x',s.x);c.setAttribute('y',s.y+6);c.setAttribute('text-anchor','middle');
  c.setAttribute('font-size','16');c.textContent='✅';c.style.opacity=0;c.dataset.f=s.f;checks.appendChild(c);}});
function draw(p){{const pt=path.getPointAtLength(L*p);
  car.setAttribute('transform','translate('+pt.x+' '+pt.y+')');
  done.style.strokeDashoffset=L*(1-p);
  [...checks.children].forEach(c=>c.style.opacity=(p>=+c.dataset.f-0.001 && p>0)?1:0);}}
const t0=performance.now(), dur=p1===p0?1:2500;
(function step(t){{const k=Math.min((t-t0)/dur,1), e=1-Math.pow(1-k,3);
  draw(p0+(p1-p0)*e); if(k<1) requestAnimationFrame(step);}})(t0);
</script>"""

# ---------- Page unique ----------
def logo_html(names, alt):
    for n in names:
        p = ASSETS / n
        if p.exists():
            mime = "jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else "png"
            return f'<div class="logo"><img alt="{alt}" src="data:image/{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"></div>'
    return '<div class="logo"></div>'

def admin_panel():
    if not admin_password:
        st.error("Mot de passe non configuré : ajoutez ADMIN_PASSWORD dans les Secrets.")
        return
    if st.text_input("Mot de passe organisateur", type="password") != admin_password:
        st.info("Saisissez le mot de passe pour ajouter un don.")
        return
    st.caption("Montant du don : 1 € = 1 km")
    cols = st.columns(5)
    for col, v in zip(cols, (5, 10, 20, 50, 100)):
        if col.button(f"+{v}", key=f"q{v}", use_container_width=True):
            add_donation(v, "")
            st.toast(f"{v} km ajoutés 🚐")
            st.rerun()
    with st.form("don", clear_on_submit=True):
        km = st.number_input("Autre montant (€)", min_value=1, max_value=100000, value=10)
        note = st.text_input("Note facultative", placeholder="Ex. : boîte à dons")
        if st.form_submit_button("✔ Valider le don", use_container_width=True):
            add_donation(km, note)
            st.toast(f"{km} km ajoutés 🚐")
            st.rerun()
    with st.expander("Corriger / sauvegarder"):
        if st.button("↩ Annuler le dernier don", use_container_width=True):
            undo_last()
            st.rerun()
        st.download_button("💾 Sauvegarder la liste (CSV)", export_csv(), "dons_telethon.csv",
                           "text/csv", use_container_width=True)
        if st.checkbox("Je veux tout effacer") and st.button("Effacer définitivement"):
            db.execute("DELETE FROM donations"); db.commit()
            st.rerun()

@st.fragment(run_every=None if mode == "admin" else 10)
def page():
    total = total_km()
    pct = min(total / goal, 1.0)
    st.markdown(
        '<div class="top">' + logo_html(["logo_vieux_volants_vimeu.jpg", "logo_asso.png"], "Les Vieux Volants du Vimeu")
        + '<div class="t"><h1>1 € = 1 KILOMÈTRE</h1><p>Le grand voyage solidaire du Téléthon</p></div>'
        + logo_html(["logo_telethon.png"], "AFM-Téléthon") + '</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="metric"><small>Kilomètres parcourus</small><strong>{fmt(total)} km</strong></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric"><small>Objectif collectif</small><strong>{fmt(goal)} km</strong></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric"><small>{pct*100:.0f} % de l\'objectif atteint</small>'
                f'<strong>{fmt(total)} €</strong><div class="bar"><i style="width:{pct*100:.1f}%"></i></div></div>',
                unsafe_allow_html=True)

    left, right = st.columns([3.1, 1], gap="medium")
    with left:
        prev = st.session_state.get("map_total")
        if prev != total or "map_html" not in st.session_state:
            st.session_state.map_html = build_map(prev or 0, total)
            st.session_state.map_total = total
        components.html(st.session_state.map_html, height=560)
    with right:
        with st.container(border=True, height=620):
            if mode == "admin":
                st.subheader("Ajouter un don")
                admin_panel()
                st.divider()
            else:
                st.subheader("Merci à tous !")
            st.markdown("**Derniers dons**")
            rows = recent(5 if mode == "admin" else 9)
            if rows:
                for km, note, when in rows:
                    st.markdown(f"**+{km} km**" + (f" — {note}" if note else ""))
                    st.caption(when)
            else:
                st.caption("Les premiers kilomètres n'attendent que vous !")
            st.caption("Ensemble, faisons avancer la solidarité ! — Les Vieux Volants du Vimeu, au profit de l’AFM-Téléthon")
    if total >= goal and not st.session_state.get("balloons"):
        st.session_state.balloons = True
        st.balloons()

page()
