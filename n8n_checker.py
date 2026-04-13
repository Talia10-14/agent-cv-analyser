"""
N8N Workflow Status Checker - Monitor N8N availability with caching.
"""

import streamlit as st
import requests
from config import N8N_WEBHOOK
from urllib.parse import urlparse


@st.cache_data(ttl=30)
def check_n8n_status() -> tuple[bool, str]:
    """
    Check if N8N webhook is reachable.
    
    Returns:
        Tuple of (is_online: bool, status_text: str)
    """
    try:
        # Extract base URL from webhook (e.g., http://localhost:5678)
        parsed = urlparse(N8N_WEBHOOK)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Try to reach the base URL with 2s timeout
        response = requests.head(base_url, timeout=2, allow_redirects=True)
        
        if response.status_code < 500:
            return True, "online"
        else:
            return False, "offline"
    except (requests.Timeout, requests.ConnectionError, Exception):
        return False, "offline"
