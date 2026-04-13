import streamlit as st
import requests
import os
import shutil
import io
from datetime import datetime
from analyzer import analyser_cv, analyser_plusieurs_cvs, extraire_texte_pdf
from sanitizer import sanitize, sanitize_list, sanitize_dict
from config import get_groq_api_key, ConfigError, MAX_FILE_SIZE, DEFAULT_POSITION, N8N_WEBHOOK
from rate_limiter import limiter
from report_generator import CVReportGenerator
from utils import score_class, score_label, create_radar_chart
from cv_validator import is_likely_cv
from i18n import get_text
from n8n_checker import check_n8n_status
from themes import get_theme_css, THEMES
import plotly.graph_objects as go

# Validate API key at startup
try:
    get_groq_api_key()
except ConfigError as e:
    st.error(f"🔴 {str(e)}")
    st.stop()

st.set_page_config(
    page_title="CV Analyzer — AI Powered",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for history
if "historique" not in st.session_state:
    st.session_state["historique"] = []

# Initialize language
if "language" not in st.session_state:
    st.session_state["language"] = "en"

# Initialize theme
if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"

# ─── GLOBAL STYLES ─────────────────────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@400;500&family=Inter:wght@300;400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
""", unsafe_allow_html=True)

# Load external CSS
try:
    with open("static/style.css", "r") as f:
        external_css = f.read()
except FileNotFoundError:
    external_css = ""

# Inject theme CSS + external CSS
theme_css = get_theme_css(st.session_state["theme"])
st.markdown(f"<style>{theme_css}\n{external_css}</style>", unsafe_allow_html=True)


# ─── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 0.5rem 0 1.5rem 0;">
        <div style="font-family:'Syne',sans-serif; font-weight:800; font-size:1.2rem; color:#39FF14; letter-spacing:0.02em;">
            CV ANALYZER
        </div>
        <div style="font-family:'DM Mono',monospace; font-size:0.7rem; color:#4A6A4A; margin-top:0.2rem; letter-spacing:0.06em;">
            POWERED BY AI · GROQ + LLAMA
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Language selector
    lang = st.selectbox(
        get_text("language", st.session_state["language"]),
        options=["en", "fr"],
        format_func=lambda x: "English" if x == "en" else "Français",
        label_visibility="collapsed"
    )
    if lang != st.session_state["language"]:
        st.session_state["language"] = lang
        st.rerun()
    
    # Theme selector
    theme_options = {k: v["name"] for k, v in THEMES.items()}
    theme = st.selectbox(
        "Theme",
        options=list(THEMES.keys()),
        format_func=lambda x: theme_options[x],
        label_visibility="collapsed",
        key="theme_select"
    )
    if theme != st.session_state["theme"]:
        st.session_state["theme"] = theme
        st.rerun()
    
    # N8N Status indicator
    is_online, status = check_n8n_status()
    status_color = "#39FF14" if is_online else "#999999"
    status_text = get_text("n8n_online", st.session_state["language"]) if is_online else get_text("n8n_offline", st.session_state["language"])
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:0.5rem; font-family:'DM Mono',monospace; font-size:0.7rem; color:#7A9A7A; margin-bottom:1rem; padding:0.5rem; background:rgba(57,255,20,0.05); border-radius:0.25rem;">
        <span style="color:{status_color}; font-size:0.9rem;">●</span>
        <span>{get_text("n8n_status", st.session_state["language"])}: {status_text}</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-label">' + get_text("sidebar_config", st.session_state["language"]) + '</div>', unsafe_allow_html=True)

    poste_vise = st.text_input(
        get_text("target_position", st.session_state["language"]),
        value=DEFAULT_POSITION,
        placeholder="e.g., Senior DevOps Engineer",
        label_visibility="visible"
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-label">' + get_text("sidebar_criteria", st.session_state["language"]) + '</div>', unsafe_allow_html=True)
    
    competences_requises = st.text_area(
        get_text("required_skills", st.session_state["language"]),
        value="",
        placeholder="Python\nDocker\nKubernetes",
        height=80,
        label_visibility="visible"
    )
    
    experience_min = st.slider(
        get_text("min_experience", st.session_state["language"]),
        min_value=0,
        max_value=15,
        value=2,
        label_visibility="visible"
    )
    
    score_seuil = st.slider(
        get_text("auto_reject_below", st.session_state["language"]),
        min_value=0,
        max_value=100,
        value=40,
        step=5,
        label_visibility="visible"
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-label">' + get_text("sidebar_how", st.session_state["language"]) + '</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style="font-size:0.82rem; color:#7A9A7A; line-height:1.9;">
        <span style="color:#39FF14; font-family:'DM Mono',monospace;">01</span> — {get_text("upload_pdfs", st.session_state["language"])}<br>
        <span style="color:#39FF14; font-family:'DM Mono',monospace;">02</span> — {get_text("text_extraction", st.session_state["language"])}<br>
        <span style="color:#39FF14; font-family:'DM Mono',monospace;">03</span> — {get_text("ai_analysis", st.session_state["language"])}<br>
        <span style="color:#39FF14; font-family:'DM Mono',monospace;">04</span> — {get_text("score_rank_export", st.session_state["language"])}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-family:'DM Mono',monospace; font-size:0.65rem; color:#2D4A2D; text-align:center; border-top:1px solid rgba(57,255,20,0.08); padding-top:1rem;">
        LLaMA 3.3 · 70B · VERSATILE
    </div>
    """, unsafe_allow_html=True)

# ─── HEADER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="display:flex; align-items:flex-end; justify-content:space-between; margin-bottom:2rem; padding-bottom:1.5rem; border-bottom:1px solid rgba(57,255,20,0.12);">
    <div>
        <div style="font-family:'Syne',sans-serif; font-weight:800; font-size:2.2rem; color:#E8F5E8; line-height:1.1;">
            {get_text("app_subtitle", st.session_state["language"]).split()[0]}<br>
            <span style="color:#39FF14;">{" ".join(get_text("app_subtitle", st.session_state["language"]).split()[1:])}</span>
        </div>
        <div style="font-family:'Inter',sans-serif; font-size:0.875rem; color:#4A6A4A; margin-top:0.5rem;">
            {get_text("app_description", st.session_state["language"])}
        </div>
    </div>
    <div style="font-family:'DM Mono',monospace; font-size:0.7rem; color:#2D4A2D; text-align:right; line-height:2;">
        <span style="color:#39FF14;">●</span> {get_text("system_online", st.session_state["language"])}<br>
        {get_text("groq_connected", st.session_state["language"])}
    </div>
</div>
""", unsafe_allow_html=True)


def afficher_resultat(r):
    if r is None:
        st.error("Failed to analyze CV. Please try again.")
        return

    nom = sanitize(r.get('nom', 'Candidate'))
    poste_actuel = sanitize(r.get('poste_actuel', ''))
    score_global = r.get("score_global", 0)
    score_tech   = r.get("score_technique", 0)
    score_exp    = r.get("score_experience", 0)

    # ── Candidate header
    st.markdown(f"""
    <p class="candidate-name">{nom}</p>
    <p class="candidate-role">{poste_actuel or 'Position not specified'}</p>
    """, unsafe_allow_html=True)

    # ── Score row
    st.markdown('<div class="section-label">' + get_text("scores", st.session_state["language"]) + '</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        sc = score_class(score_global)
        st.markdown(f"""
        <div class="cv-card" style="text-align:center; padding:1rem;">
            <div style="font-family:'DM Mono',monospace; font-size:0.65rem; color:var(--text-dim); text-transform:uppercase; letter-spacing:.1em; margin-bottom:.4rem;">{get_text("global", st.session_state["language"])}</div>
            <div style="font-family:'Syne',sans-serif; font-weight:800; font-size:2rem; color:{score_label(score_global)};">{score_global}<span style="font-size:1rem; font-weight:400;">%</span></div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="cv-card" style="text-align:center; padding:1rem;">
            <div style="font-family:'DM Mono',monospace; font-size:0.65rem; color:var(--text-dim); text-transform:uppercase; letter-spacing:.1em; margin-bottom:.4rem;">{get_text("technical", st.session_state["language"])}</div>
            <div style="font-family:'Syne',sans-serif; font-weight:800; font-size:2rem; color:{score_label(score_tech)};">{score_tech}<span style="font-size:1rem; font-weight:400;">%</span></div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="cv-card" style="text-align:center; padding:1rem;">
            <div style="font-family:'DM Mono',monospace; font-size:0.65rem; color:var(--text-dim); text-transform:uppercase; letter-spacing:.1em; margin-bottom:.4rem;">{get_text("experience", st.session_state["language"])}</div>
            <div style="font-family:'Syne',sans-serif; font-weight:800; font-size:2rem; color:{score_label(score_exp)};">{score_exp}<span style="font-size:1rem; font-weight:400;">%</span></div>
        </div>
        """, unsafe_allow_html=True)

    # Progress bar
    st.progress(score_global / 100 if score_global else 0)

    # ── Radar
    st.markdown('<div class="section-label" style="margin-top:1.25rem;">' + get_text("score_distribution", st.session_state["language"]) + '</div>', unsafe_allow_html=True)
    fig = create_radar_chart(score_global, score_tech, score_exp)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.divider()

    # ── Skills
    competences = sanitize_list(r.get("competences", []) or r.get("points_forts", []))
    if competences:
        st.markdown('<div class="section-label">' + get_text("key_skills", st.session_state["language"]) + '</div>', unsafe_allow_html=True)
        tags_html = "".join([f'<span class="skill-tag">{s}</span>' for s in competences[:14]])
        st.markdown(f'<div style="line-height:2.4;">{tags_html}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    st.divider()

    # ── Strengths / Weaknesses
    strengths  = sanitize_list(r.get("forces", []) or r.get("points_forts", []))
    weaknesses = sanitize_list(r.get("faiblesses", []) or r.get("points_faibles", []))

    col_s, col_w = st.columns(2, gap="medium")
    with col_s:
        if strengths:
            st.markdown('<div class="section-label">' + get_text("strengths", st.session_state["language"]) + '</div>', unsafe_allow_html=True)
            for s in strengths[:5]:
                st.markdown(f'<div class="list-item-pos"><span style="color:var(--green); flex-shrink:0;">✓</span>{s}</div>', unsafe_allow_html=True)
    with col_w:
        if weaknesses:
            st.markdown('<div class="section-label">' + get_text("gaps", st.session_state["language"]) + '</div>', unsafe_allow_html=True)
            for w in weaknesses[:5]:
                st.markdown(f'<div class="list-item-neg"><span style="color:var(--danger); flex-shrink:0;">!</span>{w}</div>', unsafe_allow_html=True)

    st.divider()

    # ── HR Assessment
    hr = sanitize(r.get("avis_rh", "") or r.get("resume_rh", ""))
    if hr:
        st.markdown('<div class="section-label">' + get_text("hr_assessment", st.session_state["language"]) + '</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="hr-quote">{hr}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Recommendation
    recommendation = r.get("recommendation", "") or r.get("recommandation", "")
    rec_map = {
        "KEPT":        ("✓ " + get_text("retained_text", st.session_state["language"]),          "rec-retained"),
        "CONSIDER":    ("◐ " + get_text("consider_text", st.session_state["language"]),        "rec-consider"),
        "REJECTED":    ("✕ " + get_text("rejected_text", st.session_state["language"]),    "rec-rejected"),
        "RETENU":      ("✓ " + get_text("retained_text", st.session_state["language"]),           "rec-retained"),
        "À CONSIDÉRER":("◐ " + get_text("consider_text", st.session_state["language"]),        "rec-consider"),
        "REJETÉ":      ("✕ " + get_text("rejected_text", st.session_state["language"]),    "rec-rejected"),
    }
    rec_text, rec_cls = rec_map.get(recommendation, ("— NO RECOMMENDATION", "rec-consider"))
    st.markdown('<div class="section-label">' + get_text("final_recommendation", st.session_state["language"]) + '</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="rec-banner {rec_cls}">{rec_text}</div>', unsafe_allow_html=True)

    # ── Export
    st.divider()
    st.markdown('<div class="section-label">' + get_text("export", st.session_state["language"]) + '</div>', unsafe_allow_html=True)
    try:
        report_gen = CVReportGenerator(r)
        pdf_bytes = report_gen.get_pdf_bytes()
        if pdf_bytes:
            candidate_name = sanitize(r.get('nom', 'Report')).replace(' ', '_')
            st.download_button(
                label=get_text("download_pdf", st.session_state["language"]),
                data=pdf_bytes,
                file_name=f"rapport_{candidate_name}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            st.caption("Includes: scores · skills · strengths · gaps · HR assessment · recommendation")
        else:
            st.warning("Could not generate PDF report.")
    except Exception as e:
        st.error(f"Report error: {str(e)}")


def analyser_via_n8n(texte, poste, criteres=None):
    if criteres is None:
        criteres = {}
    try:
        payload = {
            "texte_cv": texte,
            "poste_vise": poste,
            "criteres": criteres
        }
        rep = requests.post(N8N_WEBHOOK, json=payload, timeout=30)
        if rep.status_code == 200:
            data = rep.json()
            return (data[0] if isinstance(data, list) else data), True
    except Exception:
        pass
    return analyser_cv(texte, poste), False


# ─── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    get_text("tab_single", st.session_state["language"]),
    get_text("tab_batch", st.session_state["language"]),
    get_text("tab_history", st.session_state["language"])
])

# ══ TAB 1 ══════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-label">' + get_text("tab_single", st.session_state["language"]) + '</div>', unsafe_allow_html=True)
    st.markdown('<div style="color:var(--text-muted); font-size:.875rem; margin-bottom:1.5rem;">Upload one CV to receive detailed AI-powered analysis, scoring, and an exportable report.</div>', unsafe_allow_html=True)

    col_up, col_res = st.columns([1, 1.1], gap="large")

    with col_up:
        fichier = st.file_uploader("Select a CV (PDF)", type=["pdf"], label_visibility="collapsed")

        if fichier:
            if fichier.size > MAX_FILE_SIZE:
                st.error(f"File too large — max {MAX_FILE_SIZE/1024/1024:.0f} MB")
            else:
                st.markdown(f"""
                <div style="background:var(--green-faint); border:1px solid var(--border-strong); border-radius:var(--radius); padding:.75rem 1rem; margin:.75rem 0; display:flex; align-items:center; gap:.75rem; font-size:.85rem;">
                    <span style="color:var(--green);">✓</span>
                    <span style="color:var(--text); font-family:'DM Mono',monospace;">{fichier.name}</span>
                    <span style="color:var(--text-dim); margin-left:auto;">{fichier.size/1024:.0f} KB</span>
                </div>
                """, unsafe_allow_html=True)

                chemin_tmp = f"/tmp/{fichier.name}"
                with open(chemin_tmp, "wb") as f:
                    f.write(fichier.read())

                if st.button(get_text("run_analysis", st.session_state["language"]), type="primary", use_container_width=True):
                    allowed, message = limiter.check()
                    if not allowed:
                        st.warning(message)
                    else:
                        try:
                            with st.status(get_text("tab_single", st.session_state["language"]) + "…", expanded=True) as status:
                                st.write(get_text("extracting_text", st.session_state["language"]))
                                texte = extraire_texte_pdf(chemin_tmp)
                                
                                if not texte.strip():
                                    status.update(label="Extraction failed", state="error")
                                    st.error(get_text("no_text_extracted", st.session_state["language"]))
                                else:
                                    # Validate that PDF is likely a CV
                                    is_cv, reason = is_likely_cv(texte)
                                    if not is_cv:
                                        st.warning(f"⚠ {get_text('doc_not_cv', st.session_state['language'])}: {reason}")
                                        if not st.checkbox(get_text("analyze_anyway", st.session_state["language"]), key="force_analyze"):
                                            st.info(get_text("analysis_cancelled", st.session_state["language"]))
                                            st.stop()
                                    st.write(get_text("sending_model", st.session_state["language"]))
                                    
                                    # Build criteria dict
                                    criteres = {}
                                    if competences_requises:
                                        criteres["competences"] = [c.strip() for c in competences_requises.split("\n") if c.strip()]
                                    if experience_min > 0:
                                        criteres["experience_min"] = experience_min
                                    
                                    resultat, via_n8n = analyser_via_n8n(texte, poste_vise, criteres)
                                    
                                    st.write(get_text("processing_scores", st.session_state["language"]))
                                    st.session_state["resultat"] = resultat
                                    st.session_state["historique"].append({
                                        "nom": sanitize(resultat.get('nom', 'Unknown')),
                                        "score_global": resultat.get('score_global', 0),
                                        "recommandation": resultat.get('recommendation', resultat.get('recommandation', '')),
                                        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M'),
                                        "data": resultat
                                    })
                                    
                                    source = "n8n workflow" if via_n8n else "direct Groq API"
                                    status.update(label=f"Analysis complete — via {source}", state="complete", expanded=False)
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                        finally:
                            # Clean up temporary file
                            try:
                                if os.path.exists(chemin_tmp):
                                    os.remove(chemin_tmp)
                            except Exception:
                                pass
        else:
            st.markdown("""
            <div style="text-align:center; padding:3rem 1rem; color:var(--text-dim);">
                <div style="font-size:2rem; margin-bottom:.5rem; opacity:.4;">↑</div>
                <div style="font-family:'DM Mono',monospace; font-size:.75rem; letter-spacing:.08em; text-transform:uppercase;">Drop a PDF here</div>
            </div>
            """, unsafe_allow_html=True)

    with col_res:
        if "resultat" in st.session_state:
            afficher_resultat(st.session_state["resultat"])
        else:
            st.markdown("""
            <div style="height:100%; display:flex; align-items:center; justify-content:center; text-align:center; padding:3rem 1rem; border:1px dashed rgba(57,255,20,0.1); border-radius:var(--radius-lg); color:var(--text-dim);">
                <div>
                    <div style="font-size:1.75rem; opacity:.25; margin-bottom:.75rem;">◐</div>
                    <div style="font-family:'DM Mono',monospace; font-size:.75rem; letter-spacing:.06em; text-transform:uppercase; line-height:2;">
                        Results will<br>appear here
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ══ TAB 2 ══════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-label">' + get_text("batch_analysis", st.session_state["language"]) + '</div>', unsafe_allow_html=True)
    st.markdown('<div style="color:var(--text-muted); font-size:.875rem; margin-bottom:1.5rem;">' + get_text("batch_description", st.session_state["language"]) + '</div>', unsafe_allow_html=True)

    fichiers = st.file_uploader(
        get_text("upload_multiple", st.session_state["language"]),
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    if fichiers:
        fichiers_valides = [f for f in fichiers if f.size <= MAX_FILE_SIZE]
        skipped = len(fichiers) - len(fichiers_valides)

        if skipped:
            st.warning(f"{skipped} file(s) skipped — exceeded size limit")

        if fichiers_valides:
            st.markdown(f"""
            <div style="background:var(--green-faint); border:1px solid var(--border-strong); border-radius:var(--radius); padding:.75rem 1rem; font-size:.85rem; color:var(--text-muted); font-family:'DM Mono',monospace; margin-bottom:1rem;">
                <span style="color:var(--green);">{len(fichiers_valides)}</span> {get_text("files_ready", st.session_state["language"])} · {get_text("estimated_time", st.session_state["language"])}: ~{len(fichiers_valides)*8}s
            </div>
            """, unsafe_allow_html=True)

            if st.button(get_text("run_batch", st.session_state["language"]), type="primary", use_container_width=True):
                allowed, message = limiter.check()
                if not allowed:
                    st.warning(message)
                else:
                    dossier_tmp = "/tmp/cvs_batch"
                    try:
                        os.makedirs(dossier_tmp, exist_ok=True)
                        for f in fichiers_valides:
                            with open(f"{dossier_tmp}/{f.name}", "wb") as out:
                                out.write(f.read())

                        with st.status(f"Analyzing {len(fichiers_valides)} CVs…", expanded=True) as status:
                            resultats = analyser_plusieurs_cvs(dossier_tmp, poste_vise)
                            if resultats:
                                st.write(f"✓ {len(resultats)} CVs processed — Sorting by global score…")
                                status.update(label=f"Complete: {len(resultats)} CVs ranked", state="complete", expanded=False)

                        if resultats:
                            st.success(f"{len(resultats)} CVs analyzed — ranked by global score")
                            st.divider()

                            # ─── Compare candidates side-by-side
                            if len(resultats) >= 2:
                                st.markdown('<div class="section-label">' + get_text("comparison", st.session_state["language"]) + '</div>', unsafe_allow_html=True)
                                st.markdown('<div style="color:var(--text-muted); font-size:.875rem; margin-bottom:1rem;">' + get_text("select_comparison", st.session_state["language"]) + '</div>', unsafe_allow_html=True)
                                
                                col_a, col_b, col_btn = st.columns([2, 2, 1])
                                candidate_names = [f"{sanitize(r.get('nom', 'Unknown'))} ({r.get('score_global', 0)}%)" for r in resultats]
                                
                                with col_a:
                                    selected_a = st.selectbox(
                                        get_text("candidate_a", st.session_state["language"]),
                                        options=candidate_names,
                                        label_visibility="collapsed",
                                        key="cand_a"
                                    )
                                
                                with col_b:
                                    selected_b = st.selectbox(
                                        get_text("candidate_b", st.session_state["language"]),
                                        options=candidate_names,
                                        label_visibility="collapsed",
                                        key="cand_b"
                                    )
                                
                                with col_btn:
                                    compare_clicked = st.button(get_text("compare_button", st.session_state["language"]), use_container_width=True, type="primary")
                                
                                if compare_clicked and selected_a != selected_b:
                                    idx_a = candidate_names.index(selected_a)
                                    idx_b = candidate_names.index(selected_b)
                                    
                                    st.divider()
                                    st.markdown('<div class="section-label">Side-by-Side Comparison</div>', unsafe_allow_html=True)
                                    
                                    col_comp_a, col_comp_b = st.columns(2, gap="large")
                                    with col_comp_a:
                                        st.markdown(f'<div style="font-weight:800; color:#39FF14; margin-bottom:1rem;">{candidate_names[idx_a]}</div>', unsafe_allow_html=True)
                                        afficher_resultat(resultats[idx_a])
                                    with col_comp_b:
                                        st.markdown(f'<div style="font-weight:800; color:#39FF14; margin-bottom:1rem;">{candidate_names[idx_b]}</div>', unsafe_allow_html=True)
                                        afficher_resultat(resultats[idx_b])
                                elif compare_clicked:
                                    st.warning("Please select two different candidates to compare.")
                            
                            st.divider()
                            st.markdown('<div class="section-label">' + get_text("candidate_ranking", st.session_state["language"]) + '</div>', unsafe_allow_html=True)
                            
                            medals = ["01", "02", "03"]
                            for i, r in enumerate(resultats, 1):
                                st.session_state["historique"].append({
                                    "nom": sanitize(r.get('nom', 'Unknown')),
                                    "score_global": r.get('score_global', 0),
                                    "recommandation": r.get('recommendation', r.get('recommandation', '')),
                                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M'),
                                    "data": r
                                })
                                nom   = sanitize(r.get('nom', 'Unnamed'))
                                score = r.get('score_global', 0)
                                poste = sanitize(r.get('poste_actuel', ''))
                                rank  = medals[i-1] if i <= 3 else f"{i:02d}"
                                sc    = score_class(score)
                                lbl   = score_label(score)

                                with st.expander(
                                    f"#{rank}  {nom}  ·  {score}%  ·  {poste}",
                                    expanded=(i == 1)
                                ):
                                    afficher_resultat(r)
                            
                            # Export buttons
                            st.divider()
                            st.markdown('<div class="section-label">' + get_text("export_results", st.session_state["language"]) + '</div>', unsafe_allow_html=True)
                            
                            import pandas as pd
                            
                            # Create dataframe
                            export_data = []
                            for idx, r in enumerate(resultats, 1):
                                export_data.append({
                                    "Rank": idx,
                                    "Name": sanitize(r.get('nom', '')),
                                    "Current Position": sanitize(r.get('poste_actuel', '')),
                                    "Global Score": r.get('score_global', 0),
                                    "Technical Score": r.get('score_technique', 0),
                                    "Experience Score": r.get('score_experience', 0),
                                    "Recommendation": r.get('recommandation', r.get('recommendation', '')),
                                    "Key Skills": ", ".join(r.get('competences', [])[:5]),
                                    "Strengths": "; ".join(r.get('forces', r.get('points_forts', []))[:3]),
                                    "HR Assessment": r.get('resume_rh', r.get('avis_rh', ''))
                                })
                            
                            df_export = pd.DataFrame(export_data)
                            
                            col_csv, col_xlsx = st.columns(2)
                            with col_csv:
                                csv_data = df_export.to_csv(index=False).encode('utf-8')
                                st.download_button(
                                    get_text("export_csv", st.session_state["language"]),
                                    data=csv_data,
                                    file_name="cv_ranking.csv",
                                    mime="text/csv",
                                    use_container_width=True
                                )
                            
                            with col_xlsx:
                                import openpyxl
                                xlsx_buffer = io.BytesIO()
                                with pd.ExcelWriter(xlsx_buffer, engine='openpyxl') as writer:
                                    df_export.to_excel(writer, index=False, sheet_name='CV Ranking')
                                st.download_button(
                                    get_text("export_excel", st.session_state["language"]),
                                    data=xlsx_buffer.getvalue(),
                                    file_name="cv_ranking.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True
                                )
                        else:
                            st.warning("No results generated. Please verify the files.")
                    finally:
                        # Clean up temporary batch folder
                        shutil.rmtree(dossier_tmp, ignore_errors=True)
        else:
            if not fichiers:
                st.info("📁 Upload PDF files to start batch analysis")
            else:
                st.error("All uploaded files exceed the 10 MB size limit. Please upload smaller files.")

# ══ TAB 3 ══════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-label">' + get_text("session_history", st.session_state["language"]) + '</div>', unsafe_allow_html=True)
    st.markdown('<div style="color:var(--text-muted); font-size:.875rem; margin-bottom:1.5rem;">' + get_text("all_analyses", st.session_state["language"]) + '</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns([4, 1])
    with col_b:
        if "confirm_clear" not in st.session_state:
            st.session_state["confirm_clear"] = False
        
        if not st.session_state["confirm_clear"]:
            if st.button(get_text("clear", st.session_state["language"]), use_container_width=True):
                st.session_state["confirm_clear"] = True
                st.rerun()
        else:
            st.warning(get_text("confirm_clear", st.session_state["language"]))
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button(get_text("yes_clear", st.session_state["language"]), type="primary", use_container_width=True):
                    st.session_state["historique"] = []
                    st.session_state["confirm_clear"] = False
                    st.rerun()
            with col_no:
                if st.button(get_text("cancel", st.session_state["language"]), use_container_width=True):
                    st.session_state["confirm_clear"] = False
                    st.rerun()

    st.divider()

    if st.session_state["historique"]:
        import pandas as pd
        df = pd.DataFrame(st.session_state["historique"])
        df_display = df.rename(columns={
            "nom": "Candidate",
            "score_global": "Score (%)",
            "recommandation": "Recommendation",
            "timestamp": "Analyzed At"
        })

        def color_rec(val):
            v = str(val).upper()
            if "RETENU" in v or "KEPT" in v: return "background:#0D1F0D; color:#39FF14"
            if "CONSIDÉR" in v or "CONSIDER" in v: return "background:#1F1800; color:#FFB800"
            if "REJET" in v or "REJECTED" in v: return "background:#1F0808; color:#FF4444"
            return ""

        styled = df_display.style.map(
            lambda x: color_rec(x) if isinstance(x, str) else "",
            subset=["Recommendation"]
        ).format({"Score (%)": "{:.0f}"})

        st.dataframe(styled, use_container_width=True, hide_index=True, height=min(len(df) * 38 + 50, 500))
        st.divider()

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(get_text("average_score", st.session_state["language"]), f"{df['score_global'].mean():.1f}%")
        with c2:
            st.metric(get_text("total_analyses", st.session_state["language"]), len(df))
        with c3:
            retained = len([r for r in df["recommandation"] if "RETENU" in str(r).upper() or "KEPT" in str(r).upper()])
            st.metric(get_text("retained", st.session_state["language"]), f"{retained}/{len(df)}")
        
        # View past report
        st.divider()
        st.markdown('<div class="section-label">' + get_text("view_past_report", st.session_state["language"]) + '</div>', unsafe_allow_html=True)
        
        noms = [f"{h['timestamp']} — {h['nom']} ({h['score_global']}%)" for h in st.session_state["historique"]]
        selected = st.selectbox(get_text("select_report", st.session_state["language"]), options=["— select —"] + noms, label_visibility="collapsed")
        
        if selected != "— select —":
            idx = noms.index(selected)
            report_data = st.session_state["historique"][idx].get("data")
            if report_data:
                st.divider()
                st.markdown('<div class="section-label">' + get_text("full_report", st.session_state["language"]) + '</div>', unsafe_allow_html=True)
                afficher_resultat(report_data)
    else:
        st.markdown(f"""
        <div style="text-align:center; padding:3rem; border:1px dashed rgba(57,255,20,0.08); border-radius:var(--radius-lg); color:var(--text-dim);">
            <div style="font-family:'DM Mono',monospace; font-size:.75rem; letter-spacing:.08em; text-transform:uppercase; line-height:2.5;">
                {get_text("no_analyses", st.session_state["language"])}<br>
                <span style="opacity:.5;">{get_text("start_analyzing", st.session_state["language"])}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)