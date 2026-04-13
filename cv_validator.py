"""
CV Validation utilities.
Light heuristic checks for PDF content validation.
"""

def is_likely_cv(texte: str) -> tuple:
    """
    Heuristic check to verify extracted text looks like a CV.
    
    Args:
        texte: Extracted text from PDF
        
    Returns:
        tuple: (is_cv: bool, reason: str)
    """
    if len(texte.strip()) < 100:
        return False, "Text too short (less than 100 characters extracted)"
    
    cv_keywords = [
        "expérience", "experience", "formation", "education", "compétences",
        "skills", "emploi", "work", "diplôme", "degree", "université",
        "university", "stage", "internship", "poste", "position", "cv",
        "resume", "curriculum", "professionnel", "professional"
    ]
    
    texte_lower = texte.lower()
    matches = sum(1 for kw in cv_keywords if kw in texte_lower)
    
    if matches < 2:
        return False, f"No CV-related keywords detected (found {matches}, minimum 2 required)"
    
    return True, "OK"
