"""
Theme management - Dark and Light mode support with CSS variables.
"""

THEMES = {
    "dark": {
        "name": "🌙 Dark",
        "css_vars": {
            "--green": "#39FF14",
            "--green-faint": "rgba(57, 255, 20, 0.08)",
            "--black": "#080C08",
            "--surface": "#0D120D",
            "--surface-alt": "#0F150F",
            "--text": "#E8F5E8",
            "--text-dim": "#7A9A7A",
            "--text-muted": "#5A7A5A",
            "--border-strong": "rgba(57, 255, 20, 0.2)",
            "--border-subtle": "rgba(57, 255, 20, 0.08)",
            "--warn": "#FFB800",
            "--danger": "#FF4444",
            "--radius": "0.375rem",
            "--radius-lg": "0.75rem",
        }
    },
    "light": {
        "name": "☀️ Light",
        "css_vars": {
            "--green": "#1DB81D",
            "--green-faint": "rgba(29, 184, 29, 0.08)",
            "--black": "#FFFFFF",
            "--surface": "#F8F8F8",
            "--surface-alt": "#F0F0F0",
            "--text": "#1A1A1A",
            "--text-dim": "#666666",
            "--text-muted": "#999999",
            "--border-strong": "rgba(29, 184, 29, 0.2)",
            "--border-subtle": "rgba(29, 184, 29, 0.08)",
            "--warn": "#FF9800",
            "--danger": "#F44336",
            "--radius": "0.375rem",
            "--radius-lg": "0.75rem",
        }
    }
}

def get_theme_css(theme: str = "dark") -> str:
    """
    Get CSS with theme variables injected.
    
    Args:
        theme: "dark" or "light"
        
    Returns:
        CSS string with theme variables
    """
    if theme not in THEMES:
        theme = "dark"
    
    vars_dict = THEMES[theme]["css_vars"]
    var_declarations = "\n".join([f"  {k}: {v};" for k, v in vars_dict.items()])
    
    return f"""
:root {{
{var_declarations}
}}

body {{
  background-color: var(--surface) !important;
  color: var(--text) !important;
}}

[data-testid="stAppViewContainer"] {{
  background-color: var(--surface) !important;
}}

[data-testid="stSidebar"] {{
  background-color: var(--surface-alt) !important;
}}

.stTabs [role="tablist"] {{
  background-color: var(--surface-alt) !important;
  border-bottom: 1px solid var(--border-subtle) !important;
}}

.stTabs [role="tab"] {{
  color: var(--text-dim) !important;
}}

.stTabs [role="tab"][aria-selected="true"] {{
  color: var(--green) !important;
  border-bottom: 2px solid var(--green) !important;
}}

input, textarea, select {{
  background-color: var(--surface-alt) !important;
  color: var(--text) !important;
  border: 1px solid var(--border-strong) !important;
}}

button {{
  background-color: var(--green) !important;
  color: var(--black) !important;
}}

.stButton > button {{
  background-color: var(--green) !important;
  color: var(--black) !important;
  border: none !important;
}}

.stDataFrame {{
  background-color: var(--surface-alt) !important;
}}

[data-testid="stMetricValue"] {{
  color: var(--text) !important;
}}

[data-testid="stMetricLabel"] {{
  color: var(--text-dim) !important;
}}
"""
