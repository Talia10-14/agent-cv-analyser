# 🤖 Agent IA — Analyse Intelligente de CVs

Système d'analyse automatique de CVs propulsé par IA (Groq + LLaMA 3.3 70B).

## Fonctionnalités
- Upload de CV en PDF
- Analyse IA avec scoring automatique (technique, expérience, global)
- Détection des compétences clés
- Points forts / points faibles
- Recommandation RH automatique (RETENU / À CONSIDÉRER / REJETÉ)
- Interface web interactive (Streamlit)
- Workflow d'automatisation no-code (n8n)

## Stack technique
- **IA** : Groq API + LLaMA 3.3 70B
- **Backend** : Python 3.10
- **Interface** : Streamlit
- **Automatisation** : n8n (workflow no-code)
- **PDF** : PyPDF2

## Installation

```bash
git clone https://github.com/votre-username/agent-cv-analyzer
cd agent-cv-analyzer
pip install groq python-dotenv PyPDF2 streamlit
```

Créez un fichier `.env` :
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
## Lancement

```bash
# Interface Streamlit
streamlit run app.py

# Workflow n8n
n8n start
```

## Architecture
