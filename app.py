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
    <p>Le grand voyage solidaire du Téléthon — Les Vieux Volants du Vimeu</p></div>
  <div class="logo"><img src="data:image/png;base64,{tele}" alt="AFM-Téléthon"></div>
</div>"""

# ---------- Espace bénévoles (menu déroulant dans l'en-tête, visible avec ?mode=admin) ----------
@st.fragment  # les boutons n'actualisent que ce menu : il reste ouvert entre deux dons
def admin_panel():
    if not admin_password:
        st.error("Mot de passe non configuré : ajoutez ADMIN_PASSWORD dans les Secrets.")
        return
    if st.text_input("Mot de passe organisateur", type="password") != admin_password:
        st.info("Saisissez le mot de passe pour ajouter un don.")
        return
    st.write("**Montant du don (1 € = 1 km)**")
    cols = st.columns(5)
    for col, v in zip(cols, (5, 10, 20, 50, 100)):
        if col.button(f"+{v}", key=f"q{v}", use_container_width=True):
            add_donation(v, "")
            st.toast(f"+{v} km — total : {fmt(total_km())} km 🚐")
    with st.form("don", clear_on_submit=True):
        km = st.number_input("Autre montant (€)", min_value=1, max_value=100000, value=10)
        note = st.text_input("Note facultative", placeholder="Ex. : boîte à dons, nom du donateur…")
        if st.form_submit_button("✔ Valider le don", use_container_width=True):
            add_donation(km, note)
            st.toast(f"+{km} km — total : {fmt(total_km())} km 🚐")
    st.divider()
    if st.button("↩ Annuler le dernier don", use_container_width=True):
        undo_last()
        st.toast("Dernier don annulé")
    st.download_button("💾 Sauvegarder la liste (Excel/CSV)", export_csv(),
                       "dons_telethon.csv", "text/csv", use_container_width=True)
    with st.expander("Zone dangereuse : tout remettre à zéro"):
        if st.checkbox("Je veux effacer tous les dons") and st.button("Effacer définitivement"):
            db.execute("DELETE FROM donations"); db.commit()
            st.toast("Tous les dons ont été effacés")

if mode == "admin":
    h_left, h_right = st.columns([8, 1.7], vertical_alignment="center")
    h_left.markdown(HERO, unsafe_allow_html=True)
    with h_right.popover("🔒 Espace bénévoles", use_container_width=True):
        admin_panel()
else:
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

public_view()

st.write("")
st.markdown('<div class="footer"><b>Ensemble, faisons avancer la solidarité !</b> &nbsp;•&nbsp; '
            'Animation des Vieux Volants du Vimeu au profit de l’AFM-Téléthon</div>',
            unsafe_allow_html=True)
