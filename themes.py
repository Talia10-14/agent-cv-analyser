"""
Theme configuration - Simple dark/light theme switcher.
"""

THEMES = {
    "dark": {
        "name": "Dark",
        "primary": "#39FF14",
        "bg": "#080C08",
        "bg_alt": "#0D120D",
        "text": "#E8F5E8",
        "text_dim": "#7A9A7A",
        "text_muted": "#5A7A5A",
        "border": "rgba(57, 255, 20, 0.2)",
        "border_subtle": "rgba(57, 255, 20, 0.08)",
        "warn": "#FFB800",
        "danger": "#FF4444",
    },
    "light": {
        "name": "Light",
        "primary": "#1DB81D",
        "bg": "#FFFFFF",
        "bg_alt": "#F8F8F8",
        "text": "#1A1A1A",
        "text_dim": "#666666",
        "text_muted": "#999999",
        "border": "rgba(29, 184, 29, 0.2)",
        "border_subtle": "rgba(29, 184, 29, 0.08)",
        "warn": "#FF9800",
        "danger": "#F44336",
    }
}

def get_theme(theme_name: str = "dark") -> dict:
    """Get theme colors by name."""
    return THEMES.get(theme_name, THEMES["dark"])

