"""
Configuration module - Centralized settings and validation.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class ConfigError(Exception):
    """Configuration validation error."""
    pass


def validate_groq_api_key(key: str) -> bool:
    """
    Validate GROQ API key format.
    
    Args:
        key: API key to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not key:
        return False
    return key.startswith("gsk_") and len(key) > 20


def get_groq_api_key() -> str:
    """
    Get validated GROQ API key from environment.
    
    Returns:
        Valid API key
        
    Raises:
        ConfigError: If key is missing or invalid
    """
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        raise ConfigError(
            "❌ GROQ_API_KEY not set.\n"
            "Please add it to .env file:\n"
            "GROQ_API_KEY=gsk_YOUR_KEY_HERE"
        )
    
    if not validate_groq_api_key(api_key):
        raise ConfigError(
            f"❌ Invalid GROQ_API_KEY format.\n"
            f"Expected: gsk_... (got {api_key[:10]}***)"
        )
    
    return api_key


# Configuration constants
DEFAULT_POSITION = "AI / Automation Specialist"
N8N_WEBHOOK = os.getenv(
    "N8N_WEBHOOK", 
    "http://localhost:5678/webhook/analyser-cv"
)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_BATCH_SIZE = 50  # Max 50 CVs per batch
REQUEST_TIMEOUT = 60  # seconds
