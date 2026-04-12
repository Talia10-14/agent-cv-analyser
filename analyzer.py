from groq import Groq
import PyPDF2
import json
import os
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def extraire_texte_pdf(chemin_pdf):
    texte = ""
    with open(chemin_pdf, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            texte += page.extract_text() or ""
    return texte.strip()

def analyser_cv(texte_cv, poste_vise="Spécialiste IA / Automatisation"):
    prompt = f"""
Tu es un expert RH spécialisé en recrutement tech.
Analyse ce CV pour le poste : {poste_vise}

CV :
{texte_cv}

Retourne UNIQUEMENT un JSON valide avec cette structure exacte, sans texte avant ou après :
{{
  "nom": "nom du candidat",
  "poste_actuel": "son titre actuel",
  "experience_annees": 0,
  "competences": ["compétence1", "compétence2"],
  "score_global": 75,
  "score_technique": 80,
  "score_experience": 70,
  "points_forts": ["point 1", "point 2", "point 3"],
  "points_faibles": ["lacune 1", "lacune 2"],
  "recommandation": "RETENU",
  "resume_rh": "Résumé en 2 phrases."
}}
"""
    reponse = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "Tu es un expert RH. Tu réponds UNIQUEMENT en JSON valide, sans markdown, sans backticks, sans texte supplémentaire."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,
        max_tokens=1000
    )

    texte = reponse.choices[0].message.content.strip()

    # Nettoyer si le modèle ajoute des backticks
    if "```" in texte:
        texte = texte.split("```")[1]
        if texte.startswith("json"):
            texte = texte[4:]

    return json.loads(texte.strip())

def analyser_plusieurs_cvs(dossier, poste_vise):
    resultats = []
    fichiers = [f for f in os.listdir(dossier) if f.endswith(".pdf")]

    if not fichiers:
        print("Aucun PDF trouvé dans le dossier.")
        return []

    for fichier in fichiers:
        chemin = os.path.join(dossier, fichier)
        print(f"  Analyse de {fichier}...")
        try:
            texte = extraire_texte_pdf(chemin)
            analyse = analyser_cv(texte, poste_vise)
            analyse["fichier"] = fichier
            resultats.append(analyse)
        except Exception as e:
            print(f"  Erreur sur {fichier} : {e}")

    resultats.sort(key=lambda x: x.get("score_global", 0), reverse=True)
    return resultats

if __name__ == "__main__":
    cv_test = """
    Jean Dupont - Développeur Full Stack
    5 ans d'expérience en Python, Django, React
    Projets : chatbot IA avec OpenAI, pipeline d'automatisation Make/n8n
    Formation : Master Informatique, Université d'Abomey-Calavi
    Compétences : Python, JavaScript, Docker, API REST, LangChain
    """

    print("Test de l'analyseur IA...")
    resultat = analyser_cv(cv_test)
    print(json.dumps(resultat, indent=2, ensure_ascii=False))
