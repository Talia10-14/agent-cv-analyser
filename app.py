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

# ─── GLOBAL STYLES ─────────────────────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@400;500&family=Inter:wght@300;400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
""", unsafe_allow_html=True)

# Load external CSS
try:
    with open("static/style.css", "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("⚠ CSS file not found. Using fallback styling.")


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

    st.markdown('<div class="section-label">Configuration</div>', unsafe_allow_html=True)

    poste_vise = st.text_input(
        "Target Position",
        value=DEFAULT_POSITION,
        placeholder="e.g., Senior DevOps Engineer",
        label_visibility="visible"
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-label">Scoring criteria</div>', unsafe_allow_html=True)
    
    competences_requises = st.text_area(
        "Required skills (one per line)",
        value="",
        placeholder="Python\nDocker\nKubernetes",
        height=80,
        label_visibility="visible"
    )
    
    experience_min = st.slider(
        "Min experience (years)",
        min_value=0,
        max_value=15,
        value=2,
        label_visibility="visible"
    )
    
    score_seuil = st.slider(
        "Auto-reject below score",
        min_value=0,
        max_value=100,
        value=40,
        step=5,
        label_visibility="visible"
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-label">How it works</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:0.82rem; color:#7A9A7A; line-height:1.9;">
        <span style="color:#39FF14; font-family:'DM Mono',monospace;">01</span> — Upload PDF CVs<br>
        <span style="color:#39FF14; font-family:'DM Mono',monospace;">02</span> — Text extraction via PyPDF2<br>
        <span style="color:#39FF14; font-family:'DM Mono',monospace;">03</span> — AI analysis via Groq<br>
        <span style="color:#39FF14; font-family:'DM Mono',monospace;">04</span> — Score, rank & export
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-family:'DM Mono',monospace; font-size:0.65rem; color:#2D4A2D; text-align:center; border-top:1px solid rgba(57,255,20,0.08); padding-top:1rem;">
        LLaMA 3.3 · 70B · VERSATILE
    </div>
    """, unsafe_allow_html=True)

# ─── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex; align-items:flex-end; justify-content:space-between; margin-bottom:2rem; padding-bottom:1.5rem; border-bottom:1px solid rgba(57,255,20,0.12);">
    <div>
        <div style="font-family:'Syne',sans-serif; font-weight:800; font-size:2.2rem; color:#E8F5E8; line-height:1.1;">
            Intelligent CV<br>
            <span style="color:#39FF14;">Analysis Platform</span>
        </div>
        <div style="font-family:'Inter',sans-serif; font-size:0.875rem; color:#4A6A4A; margin-top:0.5rem;">
            Automated scoring · Candidate ranking · HR reporting
        </div>
    </div>
    <div style="font-family:'DM Mono',monospace; font-size:0.7rem; color:#2D4A2D; text-align:right; line-height:2;">
        <span style="color:#39FF14;">●</span> SYSTEM ONLINE<br>
        GROQ API CONNECTED
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
    st.markdown('<div class="section-label">Scores</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        sc = score_class(score_global)
        st.markdown(f"""
        <div class="cv-card" style="text-align:center; padding:1rem;">
            <div style="font-family:'DM Mono',monospace; font-size:0.65rem; color:var(--text-dim); text-transform:uppercase; letter-spacing:.1em; margin-bottom:.4rem;">Global</div>
            <div style="font-family:'Syne',sans-serif; font-weight:800; font-size:2rem; color:{score_label(score_global)};">{score_global}<span style="font-size:1rem; font-weight:400;">%</span></div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="cv-card" style="text-align:center; padding:1rem;">
            <div style="font-family:'DM Mono',monospace; font-size:0.65rem; color:var(--text-dim); text-transform:uppercase; letter-spacing:.1em; margin-bottom:.4rem;">Technical</div>
            <div style="font-family:'Syne',sans-serif; font-weight:800; font-size:2rem; color:{score_label(score_tech)};">{score_tech}<span style="font-size:1rem; font-weight:400;">%</span></div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="cv-card" style="text-align:center; padding:1rem;">
            <div style="font-family:'DM Mono',monospace; font-size:0.65rem; color:var(--text-dim); text-transform:uppercase; letter-spacing:.1em; margin-bottom:.4rem;">Experience</div>
            <div style="font-family:'Syne',sans-serif; font-weight:800; font-size:2rem; color:{score_label(score_exp)};">{score_exp}<span style="font-size:1rem; font-weight:400;">%</span></div>
        </div>
        """, unsafe_allow_html=True)

    # Progress bar
    st.progress(score_global / 100 if score_global else 0)

    # ── Radar
    st.markdown('<div class="section-label" style="margin-top:1.25rem;">Score distribution</div>', unsafe_allow_html=True)
    fig = create_radar_chart(score_global, score_tech, score_exp)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.divider()

    # ── Skills
    competences = sanitize_list(r.get("competences", []) or r.get("points_forts", []))
    if competences:
        st.markdown('<div class="section-label">Key skills</div>', unsafe_allow_html=True)
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
            st.markdown('<div class="section-label">Strengths</div>', unsafe_allow_html=True)
            for s in strengths[:5]:
                st.markdown(f'<div class="list-item-pos"><span style="color:var(--green); flex-shrink:0;">✓</span>{s}</div>', unsafe_allow_html=True)
    with col_w:
        if weaknesses:
            st.markdown('<div class="section-label">Gaps</div>', unsafe_allow_html=True)
            for w in weaknesses[:5]:
                st.markdown(f'<div class="list-item-neg"><span style="color:var(--danger); flex-shrink:0;">!</span>{w}</div>', unsafe_allow_html=True)

    st.divider()

    # ── HR Assessment
    hr = sanitize(r.get("avis_rh", "") or r.get("resume_rh", ""))
    if hr:
        st.markdown('<div class="section-label">HR Assessment</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="hr-quote">{hr}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Recommendation
    recommendation = r.get("recommendation", "") or r.get("recommandation", "")
    rec_map = {
        "KEPT":        ("✓ RETAINED",          "rec-retained"),
        "CONSIDER":    ("◐ TO CONSIDER",        "rec-consider"),
        "REJECTED":    ("✕ NOT RECOMMENDED",    "rec-rejected"),
        "RETENU":      ("✓ RETAINED",           "rec-retained"),
        "À CONSIDÉRER":("◐ TO CONSIDER",        "rec-consider"),
        "REJETÉ":      ("✕ NOT RECOMMENDED",    "rec-rejected"),
    }
    rec_text, rec_cls = rec_map.get(recommendation, ("— NO RECOMMENDATION", "rec-consider"))
    st.markdown('<div class="section-label">Final recommendation</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="rec-banner {rec_cls}">{rec_text}</div>', unsafe_allow_html=True)

    # ── Export
    st.divider()
    st.markdown('<div class="section-label">Export</div>', unsafe_allow_html=True)
    try:
        report_gen = CVReportGenerator(r)
        pdf_bytes = report_gen.get_pdf_bytes()
        if pdf_bytes:
            candidate_name = sanitize(r.get('nom', 'Report')).replace(' ', '_')
            st.download_button(
                label="↓ Download PDF Report",
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
tab1, tab2, tab3 = st.tabs(["Single Analysis", "Batch Analysis", "History"])

# ══ TAB 1 ══════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-label">Single CV Analysis</div>', unsafe_allow_html=True)
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

                if st.button("Run Analysis", type="primary", use_container_width=True):
                    allowed, message = limiter.check()
                    if not allowed:
                        st.warning(message)
                    else:
                        try:
                            with st.status("Analyzing CV…", expanded=True) as status:
                                st.write("📄 Extracting text from PDF…")
                                texte = extraire_texte_pdf(chemin_tmp)
                                
                                if not texte.strip():
                                    status.update(label="Extraction failed", state="error")
                                    st.error("No text could be extracted from this PDF.")
                                else:
                                    # Validate that PDF is likely a CV
                                    is_cv, reason = is_likely_cv(texte)
                                    if not is_cv:
                                        st.warning(f"⚠ This document may not be a CV: {reason}")
                                        if not st.checkbox("Analyze anyway", key="force_analyze"):
                                            st.info("Analysis cancelled.")
                                            st.stop()
                                    st.write("🤖 Sending to AI model (Groq LLaMA 3.3)…")
                                    
                                    # Build criteria dict
                                    criteres = {}
                                    if competences_requises:
                                        criteres["competences"] = [c.strip() for c in competences_requises.split("\n") if c.strip()]
                                    if experience_min > 0:
                                        criteres["experience_min"] = experience_min
                                    
                                    resultat, via_n8n = analyser_via_n8n(texte, poste_vise, criteres)
                                    
                                    st.write("📊 Processing scores and recommendations…")
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
    st.markdown('<div class="section-label">Batch CV Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div style="color:var(--text-muted); font-size:.875rem; margin-bottom:1.5rem;">Upload multiple CVs for side-by-side comparison with automatic ranking by score.</div>', unsafe_allow_html=True)

    fichiers = st.file_uploader(
        "Upload multiple CVs (PDF)",
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
                <span style="color:var(--green);">{len(fichiers_valides)}</span> file(s) ready · Estimated time: ~{len(fichiers_valides)*8}s
            </div>
            """, unsafe_allow_html=True)

            if st.button("Run Batch Analysis", type="primary", use_container_width=True):
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

                            for r in resultats:
                                st.session_state["historique"].append({
                                    "nom": sanitize(r.get('nom', 'Unknown')),
                                    "score_global": r.get('score_global', 0),
                                    "recommandation": r.get('recommendation', r.get('recommandation', '')),
                                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M'),
                                    "data": r
                                })

                            st.markdown('<div class="section-label">Candidate ranking</div>', unsafe_allow_html=True)

                            medals = ["01", "02", "03"]
                            for i, r in enumerate(resultats, 1):
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
                            st.markdown('<div class="section-label">Export results</div>', unsafe_allow_html=True)
                            
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
                                    "↓ Export CSV",
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
                                    "↓ Export Excel",
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
    st.markdown('<div class="section-label">Session history</div>', unsafe_allow_html=True)
    st.markdown('<div style="color:var(--text-muted); font-size:.875rem; margin-bottom:1.5rem;">All analyses performed during this session.</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns([4, 1])
    with col_b:
        if "confirm_clear" not in st.session_state:
            st.session_state["confirm_clear"] = False
        
        if not st.session_state["confirm_clear"]:
            if st.button("Clear", use_container_width=True):
                st.session_state["confirm_clear"] = True
                st.rerun()
        else:
            st.warning("This will delete all session history. Confirm?")
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("Yes, clear", type="primary", use_container_width=True):
                    st.session_state["historique"] = []
                    st.session_state["confirm_clear"] = False
                    st.rerun()
            with col_no:
                if st.button("Cancel", use_container_width=True):
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
            st.metric("Average Score", f"{df['score_global'].mean():.1f}%")
        with c2:
            st.metric("Total Analyses", len(df))
        with c3:
            retained = len([r for r in df["recommandation"] if "RETENU" in str(r).upper() or "KEPT" in str(r).upper()])
            st.metric("Retained", f"{retained}/{len(df)}")
        
        # View past report
        st.divider()
        st.markdown('<div class="section-label">View past report</div>', unsafe_allow_html=True)
        
        noms = [f"{h['timestamp']} — {h['nom']} ({h['score_global']}%)" for h in st.session_state["historique"]]
        selected = st.selectbox("Select a report to view", options=["— select —"] + noms, label_visibility="collapsed")
        
        if selected != "— select —":
            idx = noms.index(selected)
            report_data = st.session_state["historique"][idx].get("data")
            if report_data:
                st.divider()
                st.markdown('<div class="section-label">Full report</div>', unsafe_allow_html=True)
                afficher_resultat(report_data)
    else:
        st.markdown("""
        <div style="text-align:center; padding:3rem; border:1px dashed rgba(57,255,20,0.08); border-radius:var(--radius-lg); color:var(--text-dim);">
            <div style="font-family:'DM Mono',monospace; font-size:.75rem; letter-spacing:.08em; text-transform:uppercase; line-height:2.5;">
                No analyses yet<br>
                <span style="opacity:.5;">Start by analyzing CVs in the tabs above</span>
            </div>
        </div>
        """, unsafe_allow_html=True)