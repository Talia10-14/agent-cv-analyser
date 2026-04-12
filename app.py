import streamlit as st
import requests
import os
from analyzer import analyser_cv, analyser_plusieurs_cvs, extraire_texte_pdf

st.set_page_config(page_title="Agent IA — Analyse de CVs", page_icon="🤖", layout="wide")
st.title("🤖 Agent IA — Analyse Intelligente de CVs")
st.markdown("*Propulsé par n8n + Groq + LLaMA 3.3 70B*")
st.divider()

with st.sidebar:
    st.header("⚙️ Configuration")
    poste_vise = st.text_input("Poste recherché", value="Spécialiste IA / Automatisation")
    st.divider()
    st.markdown("**Comment ça marche ?**")
    st.markdown("1. Téléchargez un ou plusieurs CV PDF")
    st.markdown("2. Le workflow n8n déclenche l'analyse IA")
    st.markdown("3. Score, points forts/faibles")
    st.markdown("4. Recommandation automatique")

def afficher_resultat(r):
    couleur = {"RETENU": "🟢", "À CONSIDÉRER": "🟡", "REJETÉ": "🔴"}
    emoji = couleur.get(r.get("recommandation", ""), "⚪")
    st.subheader(f"{emoji} {r.get('nom', 'Candidat')}")
    st.caption(r.get("poste_actuel", ""))
    st.markdown("#### 📊 Scores")
    c1, c2, c3 = st.columns(3)
    c1.metric("Mondial", f"{r.get('score_global', 0)}/100")
    c2.metric("Technique", f"{r.get('score_technique', 0)}/100")
    c3.metric("Expérience", f"{r.get('score_experience', 0)}/100")
    st.progress(r.get("score_global", 0) / 100)
    st.markdown("#### 🛠️ Compétences détectées")
    competences = r.get("competences", [])
    st.markdown(" ".join([f"`{c}`" for c in competences]))
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### ✅ Points forts")
        for p in r.get("points_forts", []):
            st.markdown(f"- {p}")
    with col_b:
        st.markdown("#### ⚠️ Points faibles")
        for p in r.get("points_faibles", []):
            st.markdown(f"- {p}")
    st.markdown("#### 💬 Avis RH")
    st.info(r.get("resume_rh", ""))
    rec = r.get("recommandation", "")
    st.markdown("#### 🏁 Recommandation finale")
    if rec == "RETENU":
        st.success(f"✅ {rec}")
    elif rec == "À CONSIDÉRER":
        st.warning(f"🟡 {rec}")
    else:
        st.error(f"❌ {rec}")

def analyser_via_n8n(texte, poste):
    try:
        rep = requests.post(
            "http://localhost:5678/webhook/analyser-cv",
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

tab1, tab2 = st.tabs(["📄 Analyser un CV", "📊 Comparer plusieurs CVs"])

with tab1:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Upload du CV")
        fichier = st.file_uploader("Choisir un CV (PDF)", type=["pdf"])
        if fichier:
            chemin_tmp = f"/tmp/{fichier.name}"
            with open(chemin_tmp, "wb") as f:
                f.write(fichier.read())
            if st.button("🚀 Analyser ce CV", type="primary"):
                with st.spinner("Workflow n8n en cours..."):
                    try:
                        texte = extraire_texte_pdf(chemin_tmp)
                        if not texte.strip():
                            st.error("Impossible d'extraire le texte.")
                        else:
                            resultat, via_n8n = analyser_via_n8n(texte, poste_vise)
                            if via_n8n:
                                st.success("✅ Analysé via workflow n8n !")
                            else:
                                st.warning("⚠️ Analyse directe (n8n indisponible)")
                            st.session_state["resultat"] = resultat
                    except Exception as e:
                        st.error(f"Erreur : {e}")
    with col2:
        if "resultat" in st.session_state:
            afficher_resultat(st.session_state["resultat"])

with tab2:
    st.subheader("Analyse comparative de plusieurs CVs")
    fichiers = st.file_uploader("Uploader plusieurs CVs (PDF)", type=["pdf"], accept_multiple_files=True)
    if fichiers and st.button("🚀 Analyser et Comparer", type="primary"):
        dossier_tmp = "/tmp/cvs_batch"
        os.makedirs(dossier_tmp, exist_ok=True)
        for f in fichiers:
            with open(f"{dossier_tmp}/{f.name}", "wb") as out:
                out.write(f.read())
        with st.spinner(f"Analyse de {len(fichiers)} CV(s)..."):
            resultats = analyser_plusieurs_cvs(dossier_tmp, poste_vise)
        if resultats:
            st.success(f"✅ {len(resultats)} CV(s) analysés — classés par score")
            st.divider()
            for i, r in enumerate(resultats):
                couleur = {"RETENU": "🟢", "À CONSIDÉRER": "🟡", "REJETÉ": "🔴"}
                emoji = couleur.get(r.get("recommandation", ""), "⚪")
                with st.expander(f"#{i+1} {emoji} {r.get('nom','?')} — Note: {r.get('score_global',0)}/100", expanded=(i == 0)):
                    afficher_resultat(r)
