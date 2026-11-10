import base64
import csv
import io
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

try:
    import segno  # génération du QR code
except ImportError:
    segno = None

APP_DIR = Path(__file__).parent
ASSETS = APP_DIR / "assets"
DB_PATH = APP_DIR / "telethon.db"
DEFAULT_GOAL = 500
DEFAULT_DON_URL = "https://vieuxvolantsvimeu.s2.yapla.com/fr/event-133120/"

st.set_page_config(page_title="Téléthon | Les Vieux Volants du Vimeu",
                   page_icon="https://bretteville50110.fr/wp-content/uploads/2024/11/logo-telethon.jpg", layout="wide", initial_sidebar_state="collapsed")

# Palette reprise du logo AFM-Téléthon et de la camionnette
BROWN = "#3D3633"    # texte « AFM TÉLÉTHON »
MAGENTA = "#A3125F"  # « INNOVER POUR GUÉRIR »
YELLOW = "#F9C80E"   # soleil / camionnette
TEAL = "#12B5C0"
ORANGE = "#F26A1B"
GREEN = "#8CC63F"
DKTEAL = "#00596B"
BG = "#FFFDF6"


def img64(name):
    """Charge une image depuis assets/ (ou à côté de app.py) en base64."""
    for folder in (ASSETS, APP_DIR):
        p = folder / name
        if p.exists():
            return base64.b64encode(p.read_bytes()).decode()
    return ""


st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;700;800&display=swap');
html, body, .stApp, .stApp * {{ font-family:'Poppins',Arial,sans-serif; }}
.stApp {{ background:{BG}; color:{BROWN}; }}
.block-container {{ max-width:1850px; padding:1rem 1.5rem 2rem; }}
#MainMenu, footer, header {{ visibility:hidden; }}

span[data-testid="stIconMaterial"], [class*="material-symbols"] {{
  font-family:"Material Symbols Rounded" !important; }}
.rays {{ height:8px; border-radius:6px; margin:.5rem 0 1rem;
  background:linear-gradient(90deg,{DKTEAL} 0 16%,{TEAL} 16% 33%,{GREEN} 33% 50%,
  {YELLOW} 50% 66%,{ORANGE} 66% 83%,{MAGENTA} 83% 100%); }}

.hero {{ display:flex; align-items:center; justify-content:space-between; gap:1.2rem;
  background:{BROWN}; color:#fff; padding:.8rem 1.4rem; border-radius:18px;
  border-bottom:6px solid {YELLOW}; }}
.hero .titre {{ text-align:center; flex:1; }}
.hero h1 {{ font-size:clamp(1.8rem,3.6vw,3.3rem); font-weight:800; margin:0; line-height:1.1;
  color:{YELLOW}; letter-spacing:.5px; }}
.hero p {{ margin:.25rem 0 0; color:#fff; font-size:1.05rem; font-weight:500; }}
.hero .logo {{ background:#fff; border-radius:14px; padding:.35rem .7rem; display:flex; align-items:center; }}
.hero .logo img {{ height:64px; width:auto; display:block; }}
[data-testid="stPopover"] button {{ background:{YELLOW}; color:{BROWN}; font-weight:800; border:0;
  border-radius:12px; min-height:3.2rem; box-shadow:0 4px 0 rgba(0,0,0,.18); }}
[data-testid="stPopover"] button:hover {{ background:{ORANGE}; color:#fff; }}
.qr {{ display:flex; align-items:center; gap:1rem; background:#fff; border:3px solid {MAGENTA};
  border-radius:16px; padding:.7rem 1rem; margin:.9rem 0; }}
.qr img {{ width:130px; height:130px; flex:none; }}
.qr b {{ color:{MAGENTA}; font-size:1.15rem; }}
.qr span {{ color:{DKTEAL}; font-weight:700; }}
.footer {{ background:{BROWN}; color:#fff; text-align:center; border-radius:12px; border-top:4px solid {YELLOW};
  padding:.55rem 1rem; font-size:clamp(.7rem,1.1vw,.95rem); font-weight:500; white-space:nowrap;
  overflow:hidden; text-overflow:ellipsis; }}
.footer b {{ color:{YELLOW}; }}

.metric {{ color:#fff; border-radius:16px; padding:.9rem 1.3rem; margin-bottom:.8rem;
  box-shadow:0 4px 0 rgba(0,0,0,.18); }}
.metric small {{ font-size:1rem; font-weight:500; opacity:.95; }}
.metric strong {{ display:block; font-size:clamp(2rem,3.2vw,3rem); line-height:1.15; font-weight:800; }}
.m1 {{ background:{MAGENTA}; }}
.m2 {{ background:{DKTEAL}; }}
.m3 {{ background:{ORANGE}; }}

.panel {{ background:#fff; border:2px solid {YELLOW}; border-radius:16px; padding:1rem 1.2rem; }}
.panel h3 {{ color:{MAGENTA}; margin:0 0 .5rem; }}
.don {{ display:flex; justify-content:space-between; align-items:baseline; gap:.6rem;
  padding:.35rem 0; border-bottom:1px dashed #E5DCC3; }}
.don b {{ color:{DKTEAL}; }}
.don span {{ color:#8A817B; font-size:.8rem; white-space:nowrap; }}

div.stButton > button, div.stFormSubmitButton > button {{ background:{MAGENTA}; color:#fff;
  border:0; border-radius:12px; font-weight:700; min-height:3rem; font-size:1.05rem; }}
div.stButton > button:hover, div.stFormSubmitButton > button:hover {{ background:{ORANGE}; color:#fff; }}
.stProgress > div > div {{ background:#EFE6CF; height:16px; border-radius:10px; }}
.stProgress > div > div > div > div {{ background:linear-gradient(90deg,{TEAL},{GREEN},{YELLOW},{ORANGE},{MAGENTA});
  border-radius:10px; }}
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
try:
    don_url = st.secrets.get("DON_URL", "")
except Exception:
    don_url = ""
don_url = don_url or os.environ.get("DON_URL", "") or DEFAULT_DON_URL  # page de don Yapla
mode = st.query_params.get("mode", "public")

def fmt(n):
    return f"{n:,}".replace(",", " ")

@st.cache_data
def qr_uri(url):
    return segno.make(url, error="m").svg_data_uri(scale=8, border=1, dark=BROWN, light="#FFFFFF")

def qr_panel():
    if not (don_url and segno):
        return ""
    return (f'<div class="qr"><img src="{qr_uri(don_url)}" alt="QR code de don">'
            '<div><b>Donnez par carte bancaire</b><br>Scannez ce QR code avec votre téléphone'
            '<br><span>1 € donné = 1 km parcouru</span></div></div>')

# ---------- Carte animée ----------
# Coordonnées dans l'image carte_vimeu.png (705 x 470 px), nom = étape
ROUTE = [
    (221, 312, "Feuquières-en-Vimeu"),
    (188, 285, None),
    (155, 251, None),
    (128, 193, "Woincourt"),
    (155, 170, None),
    (207, 143, None),
    (279, 118, "Friville-Escarbotin"),
    (340, 111, None),
    (405, 120, None),
    (460, 135, "Fressenneville"),
    (492, 165, None),
    (527, 197, None),
    (564, 228, "Tully"),
    (575, 270, None),
    (588, 318, None),
    (594, 366, "Aigneville"),
]

MAP_HEIGHT = 600  # hauteur de secours ; la carte s'ajuste ensuite toute seule

def build_map(prev_total, total):
    img = img64("carte_vimeu.png")
    car = img64("voiture.png")
    cum, acc = [0.0], 0.0
    for a, b in zip(ROUTE, ROUTE[1:]):
        acc += ((b[0]-a[0])**2 + (b[1]-a[1])**2) ** 0.5
        cum.append(acc)
    stops = [(x, y, n, cum[i] / acc) for i, (x, y, n) in enumerate(ROUTE) if n]
    d = "M" + " L".join(f"{x} {y}" for x, y, _ in ROUTE)
    stops_js = "[" + ",".join(f'{{x:{x},y:{y},f:{f:.4f}}}' for x, y, _, f in stops) + "]"
    p0, p1 = min(prev_total / goal, 1), min(total / goal, 1)
    return f"""
<style>
 body {{ margin:0; background:{BG}; }}
 .wrap {{ position:relative; border-radius:18px; overflow:hidden; border:4px solid {YELLOW};
   box-shadow:0 6px 0 {MAGENTA}; }}
 .cap {{ text-align:center; font:800 20px Poppins,Arial,sans-serif; color:{MAGENTA}; padding:12px 0 0; }}
</style>
<div class="wrap">
 <img src="data:image/png;base64,{img}" style="display:block;width:100%;height:auto">
 <svg id="s" viewBox="0 0 705 470" style="position:absolute;inset:0;width:100%;height:100%">
  <path id="r" d="{d}" fill="none" stroke="{DKTEAL}" stroke-width="4" stroke-dasharray="2 9" stroke-linecap="round" opacity=".6"/>
  <path id="done" d="{d}" fill="none" stroke="{MAGENTA}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
  <g id="checks"></g>
  <g id="car">
   <ellipse cx="0" cy="22" rx="38" ry="6" fill="#000" opacity=".25"/>
   <image href="data:image/png;base64,{car}" x="-44" y="-25" width="88" height="45"
          style="filter:drop-shadow(0 2px 2px rgba(0,0,0,.35))"/>
  </g>
 </svg>
</div>
<div class="cap"> {fmt(total)} km parcourus sur {fmt(goal)} km</div>
<script>
const path=document.getElementById('r'), done=document.getElementById('done'),
      car=document.getElementById('car'), checks=document.getElementById('checks');
const L=path.getTotalLength(), stops={stops_js}, p0={p0}, p1={p1};
done.style.strokeDasharray=L;
stops.forEach(s=>{{const c=document.createElementNS('http://www.w3.org/2000/svg','text');
  c.setAttribute('x',s.x);c.setAttribute('y',s.y+6);c.setAttribute('text-anchor','middle');
  c.setAttribute('font-size','16');c.textContent='✅';c.style.opacity=0;c.dataset.f=s.f;checks.appendChild(c);}});
function draw(p){{const pt=path.getPointAtLength(L*p);
  car.setAttribute('transform','translate('+pt.x+' '+(pt.y-12)+')');
  done.style.strokeDashoffset=L*(1-p);
  [...checks.children].forEach(c=>c.style.opacity=(p>=+c.dataset.f-0.001 && p>0)?1:0);}}
const t0=performance.now(), dur=p1===p0?1:2500;
(function step(t){{const k=Math.min((t-t0)/dur,1), e=1-Math.pow(1-k,3);
  draw(p0+(p1-p0)*e); if(k<1) requestAnimationFrame(step);}})(t0);
function fit(){{try{{const h=document.body.offsetHeight+12, f=window.frameElement;
  if(f){{f.style.height=h+'px'; f.setAttribute('height',h);}}}}catch(e){{}}}}
window.addEventListener('load',fit); window.addEventListener('resize',fit);
if(window.ResizeObserver) new ResizeObserver(fit).observe(document.body);
fit();
</script>"""

# ---------- En-tête : logos + titre ----------
asso, tele = img64("logo_asso.png"), img64("logo_telethon.png")
HERO = f"""
<div class="hero">
  <div class="logo"><img src="data:image/png;base64,{asso}" alt="Les Vieux Volants du Vimeu"></div>
  <div class="titre"><h1>1 € = 1 KILOMÈTRE</h1>
    <p>Téléthon — Les Vieux Volants du Vimeu</p></div>
  <div class="logo"><img src="data:image/png;base64,{tele}" alt="AFM-Téléthon"></div>
</div>"""

# ---------- Mode administrateur : boutons de dons uniquement ----------
def admin_panel():
    st.title("🔒 Espace bénévoles")

    if not admin_password:
        st.error("Mot de passe non configuré : ajoutez ADMIN_PASSWORD dans les Secrets.")
        return

    password = st.text_input("Mot de passe organisateur", type="password", key="admin_password_input")
    if password != admin_password:
        st.info("Saisissez le mot de passe pour accéder aux boutons de dons.")
        return

    st.success("Accès autorisé")
    st.subheader("Ajouter un don")
    st.caption("1 € donné = 1 km parcouru")

    cols = st.columns(5)
    for col, value in zip(cols, (2, 5, 10, 20, 50)):
        if col.button(f"+{value} €", key=f"don_{value}", use_container_width=True):
            add_donation(value, "")
            st.toast(f"+{value} km — total : {fmt(total_km())} km")

    st.divider()
    st.metric("Total collecté", f"{fmt(total_km())} €")

st.markdown(HERO, unsafe_allow_html=True)
st.markdown('<div class="rays"></div>', unsafe_allow_html=True)

# ---------- Affichage public (se rafraîchit seul toutes les 10 s) ----------
@st.fragment(run_every=5)
def public_view():
    total = total_km()
    prev = st.session_state.get("prev_total", 0)
    st.session_state.prev_total = total
    # la voiture n'est redessinée que si le total change (sinon l'animation rejouerait)
    if st.session_state.get("map_total") != total or "map_html" not in st.session_state:
        st.session_state.map_html = build_map(prev if "map_total" in st.session_state else 0, total)
        st.session_state.map_total = total

    left, right = st.columns([7, 3], gap="large")

    with left:  # grande carte à gauche
        components.html(st.session_state.map_html, height=MAP_HEIGHT)

    with right:  # chiffres et derniers dons à droite
        st.markdown(f'<div class="metric m1"><small>Kilomètres parcourus</small><strong>{fmt(total)} km</strong></div>'
                    f'<div class="metric m2"><small>Objectif collectif</small><strong>{fmt(goal)} km</strong></div>'
                    f'<div class="metric m3"><small>Total des dons</small><strong>{fmt(total)} €</strong></div>',
                    unsafe_allow_html=True)
        st.progress(min(total / goal, 1.0), text=f"{min(total / goal, 1) * 100:.0f} % de l'objectif atteint"
                    + (" — Bravo, objectif atteint ! 🎉" if total >= goal else ""))
        if total >= goal:
            st.balloons()

        st.markdown(qr_panel(), unsafe_allow_html=True)
        rows = recent(5)
        html = '<div class="panel"><h3>Les derniers kilomètres solidaires</h3>'
        if rows:
            for km, note, when in rows:
                html += (f'<div class="don"><div><b>+{km} km</b>'
                         + (f" — {note}" if note else "") + f'</div><span>{when}</span></div>')
        else:
            html += "<div>Les premiers kilomètres n'attendent que vous !</div>"
        st.markdown(html + "</div>", unsafe_allow_html=True)

# ---------- Affichage selon le mode choisi ----------
if mode == "admin":
    # Mode administrateur : boutons de dons uniquement, sans la carte.
    admin_panel()
else:
    # Mode public : carte animée, compteurs et derniers dons.
    public_view()

    st.write("")
    st.markdown('<div class="footer"><b>Ensemble, faisons avancer la solidarité !</b> &nbsp;•&nbsp; '
                'Animation des Vieux Volants du Vimeu au profit de l’AFM-Téléthon</div>',
                unsafe_allow_html=True)
