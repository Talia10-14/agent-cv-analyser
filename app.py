import streamlit as st
import requests
import os
from datetime import datetime
from analyzer import analyser_cv, analyser_plusieurs_cvs, extraire_texte_pdf
from sanitizer import sanitize, sanitize_list, sanitize_dict
from config import get_groq_api_key, ConfigError, MAX_FILE_SIZE, DEFAULT_POSITION, N8N_WEBHOOK
from rate_limiter import limiter
from report_generator import CVReportGenerator
import plotly.graph_objects as go

# Validate API key at startup
try:
    get_groq_api_key()
except ConfigError as e:
    st.error(f"🔴 {str(e)}")
    st.stop()

st.set_page_config(page_title="CV Analyzer", layout="wide")

# Initialize session state for history
if "historique" not in st.session_state:
    st.session_state["historique"] = []

# Professional Design System - Senior Frontend
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
""", unsafe_allow_html=True)

# Header Section with Enhanced Visual Hierarchy
st.markdown("""
<div style="text-align: center; padding: 2rem 1rem; margin-bottom: 2rem;">
    <h1 style="margin-bottom: 0.5rem;">CV Analyzer</h1>
    <p style="font-size: 1.1rem; color: #7C4469; font-weight: 400;">Intelligent CV analysis powered by AI</p>
</div>
""", unsafe_allow_html=True)

st.divider()

with st.sidebar:
    st.markdown("""
    <div style="background: linear-gradient(135deg, #F5F3FF 0%, #EDE9FE 100%); border-radius: 10px; padding: 1.25rem; margin-bottom: 1.5rem; border-left: 4px solid #7C3AED;">
        <h3 style="color: #1E1B4B; margin-bottom: 0.5rem;">Configuration</h3>
        <p style="color: #4C4469; font-size: 0.9rem; margin: 0;">Customize your analysis parameters below.</p>
    </div>
    """, unsafe_allow_html=True)
    
    poste_vise = st.text_input(
        "Target Position", 
        value=DEFAULT_POSITION, 
        placeholder="e.g., Senior DevOps Engineer",
        help="The position that CVs will be evaluated against"
    )
    
    st.divider()
    
    st.markdown("""
    <p class="section-title"><i class="fas fa-cog"></i> How It Works</p>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="font-size: 0.9rem; line-height: 1.7; color: #4C4469;">
    <strong style="color: #1E1B4B;">1.</strong> Upload one or multiple PDF CVs<br>
    <strong style="color: #1E1B4B;">2.</strong> System extracts text using PyPDF2<br>
    <strong style="color: #1E1B4B;">3.</strong> AI analysis via Groq LLaMA 3.3 70B<br>
    <strong style="color: #1E1B4B;">4.</strong> Get comprehensive scoring & insights
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    st.markdown("""
    <p style="font-size: 0.75rem; color: #94A3B8; text-align: center; margin-top: 1rem;">
    Powered by<br>
    <strong style="color: #7C3AED;">Groq • LLaMA 3.3 70B</strong>
    </p>
    """, unsafe_allow_html=True)

def create_radar_chart(score_global, score_tech, score_exp):
    """Create a professional radar chart for CV analysis scores"""
    
    # Ensure scores are valid
    score_global = max(0, min(100, score_global or 0))
    score_tech = max(0, min(100, score_tech or 0))
    score_exp = max(0, min(100, score_exp or 0))
    
    # Create radar chart
    fig = go.Figure(data=go.Scatterpolar(
        r=[score_global, score_tech, score_exp],
        theta=['Global', 'Technical', 'Experience'],
        fill='toself',
        fillcolor='rgba(59, 130, 246, 0.3)',  # Blue with 0.3 opacity
        line=dict(color='#001F3F', width=2),  # Navy border
        name='Scores'
    ))
    
    # Update layout
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickcolor='#D1D5DB',  # Subtle gray
                gridcolor='#E5E7EB',
                tickfont=dict(size=10, color='#6B7280')
            ),
            angularaxis=dict(
                tickfont=dict(size=12, color='#374151'),
                gridcolor='#E5E7EB'
            ),
            bgcolor='rgba(255, 255, 255, 0)'  # Transparent background
        ),
        showlegend=False,
        margin=dict(l=50, r=50, t=50, b=50),
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=450,
        font=dict(family='Inter, sans-serif', size=11, color='#374151')
    )
    
    return fig

def afficher_resultat(r):
    """Display analysis results with enhanced UI/UX"""
    
    if r is None:
        st.error("Failed to analyze CV. Please try again.")
        return
    
    # Candidate Header - SANITIZE all user inputs
    nom = sanitize(r.get('nom', 'Candidate'))
    poste_actuel = sanitize(r.get('poste_actuel', ''))
    
    st.markdown(f"""
    <div style="margin-bottom: 2rem;">
        <h2 style="margin-bottom: 0.25rem;">{nom}</h2>
        <p style="color: #7C3AED; font-weight: 600; font-size: 0.95rem;">{poste_actuel or 'Position not specified'}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Score Section - Metrics Grid
    st.markdown('<p class="section-title"><i class="fas fa-chart-bar"></i> Analysis Scores</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3, gap="medium")
    
    with col1:
        score_global = r.get("score_global", 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{score_global}%</div>
            <div class="metric-label">Global Score</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        score_tech = r.get("score_technique", 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{score_tech}%</div>
            <div class="metric-label">Technical</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        score_exp = r.get("score_experience", 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{score_exp}%</div>
            <div class="metric-label">Experience</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Progress Bar
    st.progress(score_global / 100 if score_global else 0)
    
    # Radar Chart
    st.markdown('<p style="font-weight: 600; color: #7C3AED; margin-top: 1.5rem; margin-bottom: 0.5rem;">Score Distribution</p>', unsafe_allow_html=True)
    radar_fig = create_radar_chart(score_global, score_tech, score_exp)
    st.plotly_chart(radar_fig, use_container_width=True, config={"displayModeBar": False})
    
    st.divider()
    
    # Skills Section
    competences = sanitize_list(r.get("competences", []) or r.get("points_forts", []))
    if competences:
        st.markdown('<p class="section-title"><i class="fas fa-bolt"></i> Key Skills & Competencies</p>', unsafe_allow_html=True)
        
        skill_html = '<div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">'
        for skill in competences[:12]:
            skill_html += f'<span class="skill-badge">{skill}</span>'
        skill_html += '</div>'
        st.markdown(skill_html, unsafe_allow_html=True)
        st.markdown("")  # spacing
    
    st.divider()
    
    # Two-Column Layout for Strengths/Weaknesses
    col_strengths, col_weaknesses = st.columns(2, gap="medium")
    
    # Strengths Section
    weaknesses = sanitize_list(r.get("faiblesses", []) or r.get("points_faibles", []))
    strengths = sanitize_list(r.get("forces", []) or r.get("points_forts", []))
    
    with col_strengths:
        if strengths:
            st.markdown('<p class="section-title"><i class="fas fa-check-circle"></i> Strengths</p>', unsafe_allow_html=True)
            
            for strength in strengths[:4]:
                strength_safe = strength  # Already sanitized above
                st.markdown(f"""
                <div style="display: flex; gap: 0.75rem; margin-bottom: 0.75rem; padding: 0.75rem; background: linear-gradient(135deg, #F0FDF4 0%, #ECFDF5 100%); border-left: 3px solid #10B981; border-radius: 8px;">
                    <div style="font-weight: 700; color: #10B981; min-width: 20px;"><i class="fas fa-check" style="font-size: 0.9rem;"></i></div>
                    <div style="color: #166534; font-weight: 500; line-height: 1.5; font-size: 0.9rem;">{strength_safe}</div>
                </div>
                """, unsafe_allow_html=True)
    
    # Weaknesses Section
    with col_weaknesses:
        if weaknesses:
            st.markdown('<p class="section-title"><i class="fas fa-exclamation-circle"></i> Areas for Improvement</p>', unsafe_allow_html=True)
            
            for weakness in weaknesses[:4]:
                weakness_safe = weakness  # Already sanitized above
                st.markdown(f"""
                <div style="display: flex; gap: 0.75rem; margin-bottom: 0.75rem; padding: 0.75rem; background: linear-gradient(135deg, #FEF2F2 0%, #FEF1F1 100%); border-left: 3px solid #EF4444; border-radius: 8px;">
                    <div style="font-weight: 700; color: #EF4444; min-width: 20px;"><i class="fas fa-exclamation" style="font-size: 0.9rem;"></i></div>
                    <div style="color: #9F1239; font-weight: 500; line-height: 1.5; font-size: 0.9rem;">{weakness_safe}</div>
                </div>
                """, unsafe_allow_html=True)
    
    st.divider()
    
    # HR Assessment
    hr_assessment = sanitize(r.get("avis_rh", "") or r.get("resume_rh", ""))
    if hr_assessment:
        st.markdown('<p class="section-title"><i class="fas fa-briefcase"></i> HR Assessment</p>', unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #EFF6FF 0%, #F0F9FF 100%); border-left: 4px solid #2563EB; border-radius: 10px; padding: 1.25rem; color: #1E40AF; line-height: 1.7; font-weight: 500;">
            {hr_assessment}
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Recommendation Status
    recommendation = r.get("recommendation", "") or r.get("recommandation", "")
    st.markdown('<p class="section-title"><i class="fas fa-bullseye"></i> Final Recommendation</p>', unsafe_allow_html=True)
    
    rec_map = {
        "KEPT": ("✓ RETAINED", "rec-retained"),
        "CONSIDER": ("◐ CONSIDER", "rec-consider"),
        "REJECTED": ("✕ NOT RECOMMENDED", "rec-rejected"),
        "RETENU": ("✓ RETAINED", "rec-retained"),
        "À CONSIDÉRER": ("◐ CONSIDER", "rec-consider"),
        "": ("- NO RECOMMENDATION", "rec-consider")
    }
    
    rec_text, rec_class = rec_map.get(recommendation, ("- NO RECOMMENDATION", "rec-consider"))
    
    st.markdown(f"""
    <div class="rec-banner {rec_class}">
        {rec_text}
    </div>
    """, unsafe_allow_html=True)
    
    # ==================== DOWNLOAD REPORT BUTTON ====================
    st.divider()
    st.markdown('<p class="section-title"><i class="fas fa-download"></i> Export Report</p>', unsafe_allow_html=True)
    
    try:
        # Generate PDF report
        report_gen = CVReportGenerator(r)
        pdf_bytes = report_gen.get_pdf_bytes()
        
        if pdf_bytes:
            # Create filename from candidate name
            candidate_name = sanitize(r.get('nom', 'Report')).replace(' ', '_')
            filename = f"rapport_{candidate_name}.pdf"
            
            # Create download button
            st.download_button(
                label="📥 Download PDF Report",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True
            )
            st.caption("✓ Report includes: scores, skills, strengths, weaknesses, HR assessment, and recommendation")
        else:
            st.warning("❌ Could not generate PDF report. Please try again.")
    except Exception as e:
        st.error(f"❌ Error generating report: {str(e)}")

def analyser_via_n8n(texte, poste):
    try:
        rep = requests.post(
            N8N_WEBHOOK,
            json={"texte_cv": texte, "poste_vise": poste},
            timeout=30
        )
        if rep.status_code == 200:
            data = rep.json()
            if isinstance(data, list):
                return data[0], True
            return data, True
    except Exception:
        pass
    return analyser_cv(texte, poste), False

tab1, tab2, tab3 = st.tabs(["Single Analysis", "Batch Analysis", "History"])

with tab1:
    st.markdown('<p class="section-title"><i class="fas fa-file-alt"></i> Single CV Analysis</p>', unsafe_allow_html=True)
    st.markdown("Upload a single CV to receive detailed AI-powered analysis and scoring.")
    st.divider()
    
    col1, col2 = st.columns([1.2, 1], gap="large")
    
    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #F5F3FF 0%, #EDE9FE 100%); border-radius: 12px; padding: 1.5rem; border: 2px dashed #7C3AED; text-align: center;">
            <p style="color: #7C3AED; font-weight: 600; margin-bottom: 1rem;"><i class="fas fa-cloud-upload-alt"></i> Upload Your CV</p>
        </div>
        """, unsafe_allow_html=True)
        
        fichier = st.file_uploader("Select a CV file (PDF)", type=["pdf"], label_visibility="collapsed")
        
        if fichier:
            # Validate file size
            if fichier.size > MAX_FILE_SIZE:
                st.error(f"❌ File too large! Maximum: {MAX_FILE_SIZE / 1024 / 1024:.1f}MB (yours: {fichier.size / 1024 / 1024:.1f}MB)")
            else:
                st.success(f"✓ File loaded: {fichier.name} ({fichier.size / 1024 / 1024:.1f}MB)")
                chemin_tmp = f"/tmp/{fichier.name}"
                with open(chemin_tmp, "wb") as f:
                    f.write(fichier.read())
                
                # Analysis Button
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("▶ Analyze CV", type="primary", use_container_width=True):
                        # Check rate limit
                        allowed, message = limiter.check()
                        
                        if not allowed:
                            st.warning(message)
                        else:
                            with st.spinner("Analyzing CV..."):
                                try:
                                    texte = extraire_texte_pdf(chemin_tmp)
                                    if not texte.strip():
                                        st.error("Unable to extract text from PDF.")
                                    else:
                                        resultat, via_n8n = analyser_via_n8n(texte, poste_vise)
                                        if via_n8n:
                                            st.success("✓ Analyzed via n8n workflow")
                                        else:
                                            st.info("ℹ Direct analysis (n8n unavailable)")
                                        st.session_state["resultat"] = resultat
                                        
                                        # Add to history
                                        history_entry = {
                                            "nom": sanitize(resultat.get('nom', 'Unknown')),
                                            "score_global": resultat.get('score_global', 0),
                                            "recommandation": resultat.get('recommendation', resultat.get('recommandation', '')),
                                            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                        }
                                        st.session_state["historique"].append(history_entry)
                                except Exception as e:
                                    st.error(f"⚠ Error: {str(e)}")
    
    with col2:
        if "resultat" in st.session_state:
            st.markdown('<p class="section-title"><i class="fas fa-chart-bar"></i> Analysis Results</p>', unsafe_allow_html=True)
            afficher_resultat(st.session_state["resultat"])
        else:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #EFF6FF 0%, #F0F9FF 100%); border-left: 4px solid #2563EB; border-radius: 10px; padding: 1.5rem; text-align: center; color: #1E40AF;">
                <p style="margin: 0; font-weight: 500;"><i class="fas fa-clipboard-list"></i> Results will appear here after analysis</p>
            </div>
            """, unsafe_allow_html=True)

with tab2:
    st.markdown('<p class="section-title"><i class="fas fa-folder-open"></i> Batch CV Analysis</p>', unsafe_allow_html=True)
    st.markdown("Upload multiple CVs to compare candidates side-by-side with automatic ranking.")
    st.divider()
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #F5F3FF 0%, #EDE9FE 100%); border-radius: 12px; padding: 1.5rem; border: 2px dashed #7C3AED; text-align: center;">
        <p style="color: #7C3AED; font-weight: 600; margin-bottom: 1rem;"><i class="fas fa-cloud-upload-alt"></i> Upload Multiple CVs</p>
    </div>
    """, unsafe_allow_html=True)
    
    fichiers = st.file_uploader(
        "Upload multiple CVs (PDF)", 
        type=["pdf"], 
        accept_multiple_files=True,
        label_visibility="collapsed"
    )
    
    if fichiers:
        # Validate file sizes
        fichiers_valides = []
        for f in fichiers:
            if f.size > MAX_FILE_SIZE:
                st.warning(f"⚠️ Skipped {f.name}: too large ({f.size / 1024 / 1024:.1f}MB)")
            else:
                fichiers_valides.append(f)
        
        if fichiers_valides:
            st.info(f"✓ {len(fichiers_valides)} file(s) ready to analyze")
            
            col_analyze, col_compare = st.columns(2)
            with col_analyze:
                btn_analyze = st.button("▶ Analyze & Compare", type="primary", use_container_width=True)
            
            if btn_analyze:
                # Check rate limit
                allowed, message = limiter.check()
                
                if not allowed:
                    st.warning(message)
                else:
                    dossier_tmp = "/tmp/cvs_batch"
                    os.makedirs(dossier_tmp, exist_ok=True)
                    for f in fichiers_valides:
                        with open(f"{dossier_tmp}/{f.name}", "wb") as out:
                            out.write(f.read())
                    
                    with st.spinner(f"Analyzing {len(fichiers_valides)} CVs..."):
                        resultats = analyser_plusieurs_cvs(dossier_tmp, poste_vise)
                    
                    if resultats:
                        st.success(f"✓ {len(resultats)} CVs analyzed and ranked by global score")
                        st.divider()
                        
                        # Add all batch results to history
                        for resultat in resultats:
                            history_entry = {
                                "nom": sanitize(resultat.get('nom', 'Unknown')),
                                "score_global": resultat.get('score_global', 0),
                                "recommandation": resultat.get('recommendation', resultat.get('recommandation', '')),
                                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            st.session_state["historique"].append(history_entry)
                        
                        # Ranking Display
                        st.markdown('<p class="section-title"><i class="fas fa-trophy"></i> Candidate Ranking</p>', unsafe_allow_html=True)
                        
                        for i, r in enumerate(resultats, 1):
                            nom = sanitize(r.get('nom', 'Unnamed'))
                            score = r.get('score_global', 0)
                            poste = sanitize(r.get('poste_actuel', ''))
                            
                            # Medal indicators for top 3
                            medal_text = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"#{i}"
                            
                            with st.expander(
                                f"{medal_text} {nom} — Score: {score}% | {poste}",
                                expanded=(i == 1)
                            ):
                                afficher_resultat(r)
                    else:
                        st.warning("No results were generated. Please check the files and try again.")
        else:
            st.error("❌ No valid files to process (all files too large)")

with tab3:
    st.markdown('<p class="section-title"><i class="fas fa-history"></i> Analysis History</p>', unsafe_allow_html=True)
    st.markdown("View all analyses performed in this session")
    st.divider()
    
    # Clear history button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state["historique"] = []
            st.rerun()
    
    st.divider()
    
    # Display history
    if st.session_state["historique"]:
        # Create dataframe for display
        import pandas as pd
        
        df = pd.DataFrame(st.session_state["historique"])
        
        # Rename columns for display
        df_display = df.rename(columns={
            "nom": "Candidate Name",
            "score_global": "Global Score (%)",
            "recommandation": "Recommendation",
            "timestamp": "Analyzed At"
        })
        
        # Color-code recommendations
        def color_recommendation(val):
            if "RETENU" in str(val).upper() or "KEPT" in str(val).upper():
                return "background-color: #D1FAE5; color: #065F46"
            elif "CONSIDÉRER" in str(val).upper() or "CONSIDER" in str(val).upper():
                return "background-color: #FEF3C7; color: #92400E"
            elif "REJETÉ" in str(val).upper() or "REJECTED" in str(val).upper():
                return "background-color: #FEE2E2; color: #991B1B"
            else:
                return ""
        
        # Apply styling
        styled_df = df_display.style.map(
            lambda x: color_recommendation(x) if isinstance(x, str) else "",
            subset=["Recommendation"]
        ).format({
            "Global Score (%)": "{:.0f}"
        })
        
        # Display dataframe
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            height=min(len(df) * 35 + 50, 500)
        )
        
        # Summary statistics
        st.divider()
        col1, col2, col3 = st.columns(3)
        
        with col1:
            avg_score = df["score_global"].mean()
            st.metric("Average Score", f"{avg_score:.1f}%")
        
        with col2:
            total_analyses = len(df)
            st.metric("Total Analyses", total_analyses)
        
        with col3:
            # Count recommendations
            retained = len([r for r in df["recommandation"] if "RETENU" in str(r).upper() or "KEPT" in str(r).upper()])
            st.metric("Retained", f"{retained}/{total_analyses}")
    else:
        st.info("📋 No analyses yet. Upload and analyze CVs to see the history here!")
        st.markdown("""
        **How to use the history tab:**
        - Analyze CVs in the "Single Analysis" or "Batch Analysis" tabs
        - Each analysis is automatically recorded with:
          - Candidate name
          - Global score
          - Recommendation
          - Timestamp
        - Use the "Clear History" button to reset the history
        """)

