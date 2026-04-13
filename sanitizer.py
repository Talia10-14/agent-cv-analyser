"""
Sanitizer module - Protect against XSS injection.
All user inputs should pass through these functions before rendering.
"""

import html
from typing import Any, List, Optional, Dict


def sanitize(value: Any) -> str:
    """
    Escape all HTML special characters in a value.
    
    Args:
        value: Any value to sanitize (will be converted to string)
        
    Returns:
        Sanitized string safe for HTML rendering
        
    Example:
        >>> sanitize('<script>alert(1)</script>')
        '&lt;script&gt;alert(1)&lt;/script&gt;'
    """
    if value is None:
        return ""
    return html.escape(str(value))


def sanitize_list(items: List[Any]) -> List[str]:
    """
    Escape a list of items.
    
    Args:
        items: List of items to sanitize
        
    Returns:
        List of sanitized strings
    """
    return [sanitize(item) for item in items] if items else []


def sanitize_dict(data: Dict[str, Any], keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Sanitize specific keys in a dictionary.
    
    Args:
        data: Dictionary to sanitize
        keys: List of keys to sanitize (if None, sanitizes all string values)
        
    Returns:
        Dictionary with sanitized values
    """
    if not data:
        return {}
    
    result = {}
    for key, value in data.items():
        if keys is None or key in keys:
            if isinstance(value, str):
                result[key] = sanitize(value)
            elif isinstance(value, list):
                result[key] = sanitize_list(value)
            else:
                result[key] = value
        else:
            result[key] = value
    
    return result
