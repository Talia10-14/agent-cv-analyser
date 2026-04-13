from groq import Groq
import PyPDF2
import json
import os
import logging
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from config import get_groq_api_key, ConfigError

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize Groq client with validated API key
try:
    client = Groq(api_key=get_groq_api_key())
except ConfigError as e:
    logger.error(str(e))
    raise

def extraire_texte_pdf(chemin_pdf: str) -> str:
    """
    Extract text from a PDF file.
    
    Args:
        chemin_pdf (str): Path to the PDF file
        
    Returns:
        str: Extracted text from all pages
        
    Raises:
        FileNotFoundError: If PDF file not found
        RuntimeError: If text extraction fails
    """
    try:
        texte = ""
        with open(chemin_pdf, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    texte += page_text + "\n"
        return texte.strip()
    except FileNotFoundError as e:
        logger.error(f"PDF file not found: {chemin_pdf}")
        raise
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise RuntimeError(f"Failed to extract PDF text: {str(e)}")

def analyser_cv(texte_cv: str, poste_vise: str = "Spécialiste IA / Automatisation") -> Dict[str, Any]:
    """
    Analyze a CV using Groq LLaMA 3.3 70B.
    
    Args:
        texte_cv (str): CV text content to analyze
        poste_vise (str): Target position for evaluation
        
    Returns:
        Dict[str, Any]: Analysis result with keys:
            - nom (str): Candidate name
            - poste_actuel (str): Current position
            - score_global (int): Overall score 0-100
            - score_technique (int): Technical skills score
            - score_experience (int): Experience score
            - competences (list): Key skills
            - points_forts (list): Strengths
            - points_faibles (list): Weaknesses
            - recommandation (str): RETENU/À CONSIDÉRER/REJETÉ
            - resume_rh (str): HR summary
            
    Raises:
        ValueError: If CV text is empty or API response is invalid
        Exception: If API call fails
    """
    if not texte_cv or not texte_cv.strip():
        raise ValueError("CV text cannot be empty")
    
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
    
    try:
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

        # Clean if model adds backticks
        if "```" in texte:
            texte = texte.split("```")[1]
            if texte.startswith("json"):
                texte = texte[4:]

        result = json.loads(texte.strip())
        logger.info(f"CV analysis successful for {result.get('nom', 'unknown')}")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed: {e}")
        raise ValueError(f"API returned invalid JSON: {str(e)}")
    except Exception as e:
        logger.error(f"CV analysis failed: {e}")
        raise

def analyser_plusieurs_cvs(dossier: str, poste_vise: str) -> List[Dict[str, Any]]:
    """
    Analyze multiple CVs from a directory.
    
    Args:
        dossier (str): Directory containing PDF files
        poste_vise (str): Target position for evaluation
        
    Returns:
        List[Dict]: List of analysis results sorted by global score (descending)
        
    Note:
        Results are automatically sorted by score_global in descending order.
    """
    resultats = []
    fichiers = [f for f in os.listdir(dossier) if f.endswith(".pdf")]

    if not fichiers:
        logger.warning(f"No PDF files found in {dossier}")
        return []

    logger.info(f"Starting batch analysis of {len(fichiers)} CVs")
    
    for fichier in fichiers:
        chemin = os.path.join(dossier, fichier)
        try:
            logger.info(f"Analyzing {fichier}...")
            texte = extraire_texte_pdf(chemin)
            if not texte.strip():
                logger.warning(f"No text extracted from {fichier}")
                continue
            
            analyse = analyser_cv(texte, poste_vise)
            analyse["fichier"] = fichier
            resultats.append(analyse)
            logger.info(f"Successfully analyzed {fichier} - Score: {analyse.get('score_global', 'N/A')}")
        except Exception as e:
            logger.error(f"Failed to analyze {fichier}: {e}")
            continue

    # Sort by score (highest first)
    resultats.sort(key=lambda x: x.get("score_global", 0), reverse=True)
    logger.info(f"Batch analysis complete: {len(resultats)} successful, {len(fichiers) - len(resultats)} failed")
    
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
